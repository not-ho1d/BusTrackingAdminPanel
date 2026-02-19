from django.db import models
import json
# Create your models here.
class Routes(models.Model):
    route_id = models.AutoField(primary_key=True)
    route_name = models.CharField(max_length=100)
    route_data = models.CharField(default=list)
    stopsData = models.JSONField(default=list)
    def get_routeData(self):
        return json.loads(self.route_data)