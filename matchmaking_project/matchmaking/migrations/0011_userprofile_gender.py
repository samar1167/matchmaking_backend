from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('matchmaking', '0010_update_match_preference_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='gender',
            field=models.CharField(blank=True, choices=[('male', 'Male'), ('female', 'Female')], max_length=10),
        ),
        migrations.AddIndex(
            model_name='userprofile',
            index=models.Index(fields=['gender'], name='matchmaking_gender_5d3910_idx'),
        ),
    ]
