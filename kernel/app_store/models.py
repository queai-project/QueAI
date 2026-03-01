from django.db import models

# Create your models here.
class AvailableApp(models.Model):
    name = models.CharField(max_length=100)
    folder_name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=200)
    logo = models.CharField(max_length=200)
    # Entry points
    ui_entry_point = models.CharField(max_length=200)
    configuration_entry_point = models.CharField(max_length=200)
    documentation_entry_point = models.CharField(max_length=200)
    ### Metadata
    version = models.CharField(max_length=50)
    description = models.TextField()
    author = models.CharField(max_length=200)
    lic = models.CharField(max_length=100)
    ### Installation status
    is_installed = models.BooleanField(default=False)


    def __str__(self):
        return self.display_name