from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('matchmaking', '0009_userprofile_public_match'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='usermatchpreference',
            name='matchmaking_preferr_a70c58_idx',
        ),
        migrations.RemoveField(
            model_name='usermatchpreference',
            name='preferred_city',
        ),
        migrations.RemoveField(
            model_name='usermatchpreference',
            name='preferred_distance_km',
        ),
        migrations.RemoveField(
            model_name='usermatchpreference',
            name='preferred_education',
        ),
        migrations.RemoveField(
            model_name='usermatchpreference',
            name='preferred_mother_tongue',
        ),
        migrations.RemoveField(
            model_name='usermatchpreference',
            name='preferred_profession',
        ),
        migrations.RemoveField(
            model_name='usermatchpreference',
            name='preferred_religion_community',
        ),
        migrations.AlterField(
            model_name='usermatchpreference',
            name='ancient_methods',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='usermatchpreference',
            name='deal_maker',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='usermatchpreference',
            name='karmic_glue',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='usermatchpreference',
            name='modern_methods',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='usermatchpreference',
            name='sizzle',
            field=models.BooleanField(default=False),
        ),
    ]
