from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('matchmaking', '0004_userprofile_profile_picture'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuthActionToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('purpose', models.CharField(choices=[('email_verification', 'Email Verification'), ('password_reset', 'Password Reset')], max_length=32)),
                ('token', models.CharField(db_index=True, max_length=128, unique=True)),
                ('expires_at', models.DateTimeField()),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='auth_action_tokens', to='auth.user')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='authactiontoken',
            index=models.Index(fields=['user', 'purpose'], name='matchmaking_user_id_6856b8_idx'),
        ),
        migrations.AddIndex(
            model_name='authactiontoken',
            index=models.Index(fields=['purpose', 'expires_at'], name='matchmaking_purpose_0bf478_idx'),
        ),
    ]
