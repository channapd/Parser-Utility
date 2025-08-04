from django.db import models
from authApp.models import CustomUser  

class Upload(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    input_file = models.FileField(upload_to="uploads/")
    output_file = models.FileField(upload_to="downloads/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.user.username}"
