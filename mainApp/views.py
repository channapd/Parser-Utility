import os
import re
import json
import shutil
import pandas as pd
from .models import Upload, CustomUser
from django.utils import timezone
import xml.etree.ElementTree as ET
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import JsonResponse, FileResponse, Http404
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST
from django.contrib import messages



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
            USER_DIR = os.path.join(settings.MEDIA_ROOT, f"user_{user_id}")

            user.delete()

            if os.path.exists(USER_DIR):
                shutil.rmtree(USER_DIR)

            messages.success(request, 'User and associated files deleted.')
        else:
            messages.error(request, 'Cannot delete admin user.')
    except CustomUser.DoesNotExist:
        messages.error(request, 'User not found.')

    return redirect('mainApp:admin_home')


def sanitize_tag(tag):
    tag = re.sub(r'\W|^(?=\d)', '_', tag)
    return tag


def xml_to_dataframe(file_path):
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except ET.ParseError as e:
        
        with open(file_path, 'r', encoding='utf-8-sig') as file:  
            content = file.read()
            
        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML format: {str(e)}")
    
    data = []
    for item in root:
        data.append({child.tag: child.text for child in item})
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


def convert_dataframe(df, user_id, file_format, convert_to, filename, UPLOAD_DIR, DOWNLOAD_DIR):
    base_filename, _ = os.path.splitext(filename)
    converted_filename = f"{base_filename}.txt" if convert_to == "flatfile" else f"{base_filename}.{convert_to}"
    converted_file_path = os.path.join(DOWNLOAD_DIR, converted_filename)
    uploaded_file_path = os.path.join(UPLOAD_DIR, filename)
    
    if convert_to == "json":
        json_data = df.to_dict(orient="records")  
        with open(converted_file_path, "w") as f:
            json.dump(json_data, f, indent=4)
            
    elif convert_to == "xml":
        xml_data = dataframe_to_xml(df)
        with open(converted_file_path, "w") as f:
            f.write(xml_data)
            
    elif convert_to == "flatfile":
        if file_format=="json":
            convert_json_to_flatfile(uploaded_file_path, converted_file_path)
        else:
            df.to_csv(converted_file_path, sep="\t", index=False) 
        
    else:
        raise ValueError("Invalid conversion format")
    
    download_url = os.path.join(settings.MEDIA_URL, f"user_{user_id}/downloads", converted_filename)
    return converted_file_path, download_url


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
    user_id = request.user.id
    if request.method == "POST" and request.FILES.get("file"):
        file_name = request.POST.get("file_name", "") or request.FILES["file"].name
        uploaded_file = request.FILES["file"]
        file_format = request.POST.get("file_format")
        convert_to = request.POST.get("convert_to")
        
        USER_DIR = os.path.join(settings.MEDIA_ROOT, f"user_{user_id}")
        UPLOAD_DIR = os.path.join(USER_DIR, "uploads")
        DOWNLOAD_DIR = os.path.join(USER_DIR, "downloads")
        os.makedirs(USER_DIR, exist_ok=True)
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

        relative_file_path = os.path.join(f"user_{user_id}", "uploads", uploaded_file.name)
        file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)
        default_storage.save(relative_file_path, ContentFile(uploaded_file.read()))

        try:
            if file_format == "json":
                df = pd.read_json(file_path)
            elif file_format == "xml":
                df = xml_to_dataframe(file_path)
            elif file_format == "flatfile":  
                df = pd.read_csv(file_path, sep="\t", dtype=str, na_values=[""]).fillna("")
            else:
                return JsonResponse({"error": "Invalid file format"}, status=400)
            
            converted_file_path, download_url = convert_dataframe(df, user_id, file_format, convert_to, uploaded_file.name, UPLOAD_DIR, DOWNLOAD_DIR)
            
            relative_output_path = os.path.relpath(converted_file_path, settings.MEDIA_ROOT)
            upload = Upload(
                user=CustomUser.objects.get(id=user_id),
                name=file_name,
                input_file=relative_file_path,
                output_file=relative_output_path,
                created_at=timezone.now()
            )
            upload.save()
            return JsonResponse({"success": True, "message": "File converted successfully", "upload_id": upload.id})
        
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def download_file(request, file_type, upload_id):
    upload = get_object_or_404(Upload, id=upload_id)
    if upload.user != request.user:
        raise Http404("You don't have permission to access this file")
    file_field = upload.input_file if file_type == 'input' else upload.output_file
    if not file_field:
        raise Http404("File not found")
    file_path = file_field.path
    if not os.path.exists(file_path):
        raise Http404("File not found on server")
    filename = os.path.basename(file_field.name)
    response = FileResponse(open(file_path, 'rb'))
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
