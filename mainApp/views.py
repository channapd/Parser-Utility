import os
import re
import json
import shutil
import pandas as pd
import boto3  
from io import BytesIO, StringIO  
import xml.etree.ElementTree as ET
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import JsonResponse, FileResponse, Http404, HttpResponseRedirect  
from django.conf import settings
from .models import Upload, CustomUser
from botocore.exceptions import ClientError

User = get_user_model()


@login_required
def home(request):
    if request.user.is_staff:
        return redirect('mainApp:admin_home')
    
    username = request.user.username
    uploads = Upload.objects.filter(user=request.user).order_by('-created_at')
    return render(request, "mainApp/home.html", {"username": username, "uploads": uploads})

@login_required
def get_uploads(request):
    if request.method == "GET":
        try:
            uploads = Upload.objects.filter(user=request.user).order_by('-created_at')
            uploads_data = []
            
            for upload in uploads:
                uploads_data.append({
                    'id': upload.id,
                    'name': upload.name,
                    'input_file_url': upload.input_file.url,
                    'output_file_url': upload.output_file.url,
                })
            
            return JsonResponse({
                'success': True,
                'uploads': uploads_data
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    })


@user_passes_test(lambda u: u.is_staff)
def admin_home(request):
    users = User.objects.filter(is_staff=False)
    return render(request, 'mainApp/admin_home.html', {'users': users})


@login_required
def user_management(request):
    user = request.user  
    if request.method == 'POST':
        user.username = request.POST.get('username', '')
        user.company = request.POST.get('company', '')
        password = request.POST.get('password', '').strip()
        
        if password:
            user.set_password(password)
            
        user.save()
        messages.success(request, 'Profile Updated Successfully')
        return redirect('mainApp:home')

    return render(request, 'mainApp/user_management.html', {'user': user})


@require_POST
@user_passes_test(lambda u: u.is_staff)
def delete_user(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
        if not user.is_staff:
            prefix = f"user_{user_id}/"
            storage = default_storage
            if hasattr(storage, 'bucket'):
                bucket = storage.bucket
                objects_to_delete = list(bucket.objects.filter(Prefix=prefix))
                if objects_to_delete:
                    bucket.delete_objects(Delete={'Objects': [{'Key': obj.key} for obj in objects_to_delete]})

            user.delete()
            messages.success(request, "User and files deleted.")
        else:
            messages.error(request, "Cannot delete admin user.")
    except CustomUser.DoesNotExist:
        messages.error(request, "User not found.")
    except Exception as e:
        messages.error(request, "Error deleting user.")

    return redirect('mainApp:admin_home')


def sanitize_tag(tag):
    tag = re.sub(r'\W|^(?=\d)', '_', tag)
    return tag


def xml_to_dataframe(file):
    try:
        tree = ET.parse(file)
        root = tree.getroot()
    except ET.ParseError:
        content = file.read().decode('utf-8-sig')
        root = ET.fromstring(content)
    data = [{child.tag: child.text for child in item} for item in root]
    return pd.DataFrame(data)


def convert_json_to_flatfile(json_file_path, converted_file_path):
    with open(json_file_path, "r") as file:
        data = json.load(file)

    if isinstance(data, list):
        df = pd.DataFrame(data)  

    elif isinstance(data, dict):
        all_rows = []
        for key, value in data.items():
            if isinstance(value, list):  
                all_rows.extend(value)  
            else:
                all_rows.append(value)  
        
        df = pd.DataFrame(all_rows)

    else:
        raise ValueError("Invalid JSON format. Expected a list or dictionary.")

    df = df.fillna("")
    df.to_csv(converted_file_path, sep="\t", index=False)
    print(f"Conversion successful! Flat file saved at: {converted_file_path}")


def convert_dataframe(df, user_id, file_format, convert_to, filename):
    base_filename, _ = os.path.splitext(filename)
    converted_filename = f"{base_filename}.txt" if convert_to == "flatfile" else f"{base_filename}.{convert_to}"
    s3_key = f"user_{user_id}/downloads/{converted_filename}"

    output = StringIO()
    if convert_to == "json":
        json.dump(df.to_dict(orient="records"), output, indent=4)
    elif convert_to == "xml":
        output.write(dataframe_to_xml(df))
    elif convert_to == "flatfile":
        df.to_csv(output, sep="\t", index=False)
    else:
        raise ValueError("Invalid format")

    content = ContentFile(output.getvalue().encode('utf-8'))
    default_storage.save(s3_key, content)
    download_url = default_storage.url(s3_key)
    return s3_key, download_url


def dataframe_to_xml(df):
    root = ET.Element("root")
    for _, row in df.iterrows():
        item = ET.SubElement(root, "item")
        for col, val in row.items():
            safe_col = sanitize_tag(str(col))
            child = ET.SubElement(item, safe_col)
            child.text = str(val)
    return ET.tostring(root, encoding="unicode")


@csrf_exempt  
@login_required
def upload_and_convert(request):
    if request.method == "POST" and request.FILES.get("file"):
        uploaded_file = request.FILES["file"]
        file_name = request.POST.get("file_name", "") or uploaded_file.name
        file_format = request.POST.get("file_format")
        convert_to = request.POST.get("convert_to")
        user_id = request.user.id

        input_key = f"user_{user_id}/uploads/{uploaded_file.name}"

        try:
            if file_format == "json":
                df = pd.read_json(uploaded_file)
            elif file_format == "xml":
                df = xml_to_dataframe(uploaded_file)
            elif file_format == "flatfile":
                df = pd.read_csv(uploaded_file, sep="\t", dtype=str).fillna("")
            else:
                return JsonResponse({"error": "Invalid file format"}, status=400)

            
            output_key, download_url = convert_dataframe(
                df, user_id, file_format, convert_to, uploaded_file.name
            )

            
            saved_path = default_storage.save(input_key, uploaded_file)
        
            s3_url = default_storage.url(saved_path)
            
            
            upload = Upload(
                user=request.user,
                name=file_name,
                input_file=saved_path,  
                output_file=output_key,
                created_at=timezone.now()
            )
            upload.save()

            return JsonResponse({
                "success": True, 
                "message": "File converted and uploaded to S3 successfully", 
                "upload_id": upload.id,
                "s3_url": s3_url
            })
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def download_file(request, file_type, upload_id):
    upload = get_object_or_404(Upload, id=upload_id)
    if upload.user != request.user:
        raise Http404("You don't have permission to access this file")
    
    file_field = upload.input_file if file_type == 'input' else upload.output_file
    s3_key = str(file_field)  
    
    
    filename = s3_key.split("/")[-1]
    
    print(f"S3 Key: '{s3_key}'")
    print(f"Filename: '{filename}'")
    print(f"Bucket: '{settings.AWS_STORAGE_BUCKET_NAME}'")
    
    s3 = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )
    
    try:
        s3.head_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=s3_key)
        
        
        presigned_url = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 
                'Key': s3_key,
                'ResponseContentDisposition': f'attachment; filename="{filename}"'
            },
            ExpiresIn=300,  
        )
        return HttpResponseRedirect(presigned_url)
        
    except ClientError as e:
        print(f"S3 Error: {e}")
        if e.response['Error']['Code'] == 'NoSuchKey':
            raise Http404("File not found in S3")
        else:
            raise Http404("Could not access file")
    except Exception as e:
        print(f"General Error: {e}")
        raise Http404("Could not generate download link")
