"""
core/migrations/0001_initial.py

Initial schema migration:
  - core.User     (custom user model)
  - core.VehicleImage
  - core.DamageInsight
  - core.ClaimEstimate

Run with: python manage.py migrate
"""

import core.models
import django.contrib.auth.models
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        # ── User ──────────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False, help_text="Designates that this user has all permissions without explicitly assigning them.", verbose_name="superuser status")),
                ("email", models.EmailField(db_index=True, max_length=254, unique=True)),
                ("name", models.CharField(blank=True, max_length=255)),
                ("google_uid", models.CharField(blank=True, db_index=True, max_length=128)),
                ("avatar_url", models.URLField(blank=True, max_length=500)),
                ("is_active", models.BooleanField(default=True)),
                ("is_staff", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("groups", models.ManyToManyField(blank=True, help_text="The groups this user belongs to.", related_name="user_set", related_query_name="user", to="auth.group", verbose_name="groups")),
                ("user_permissions", models.ManyToManyField(blank=True, help_text="Specific permissions for this user.", related_name="user_set", related_query_name="user", to="auth.permission", verbose_name="user permissions")),
            ],
            options={"verbose_name": "User", "verbose_name_plural": "Users"},
            managers=[("objects", django.contrib.auth.models.BaseUserManager())],
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(fields=["email"], name="user_email_idx"),
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(fields=["google_uid"], name="user_google_uid_idx"),
        ),

        # ── VehicleImage ──────────────────────────────────────────────────────
        migrations.CreateModel(
            name="VehicleImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to=core.models.vehicle_image_upload_path)),
                ("image_url", models.URLField(blank=True, max_length=1000)),
                ("uploaded_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("status", models.CharField(
                    choices=[("pending","Pending"),("analyzing","Analyzing"),("analyzed","Analyzed"),("failed","Failed")],
                    db_index=True,
                    default="pending",
                    max_length=20,
                )),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="vehicle_images",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"verbose_name": "Vehicle Image", "verbose_name_plural": "Vehicle Images", "ordering": ["-uploaded_at"]},
        ),
        migrations.AddIndex(
            model_name="vehicleimage",
            index=models.Index(fields=["user", "uploaded_at"], name="vi_user_uploaded_idx"),
        ),
        migrations.AddIndex(
            model_name="vehicleimage",
            index=models.Index(fields=["status"], name="vi_status_idx"),
        ),

        # ── DamageInsight ─────────────────────────────────────────────────────
        migrations.CreateModel(
            name="DamageInsight",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("detected_part", models.CharField(blank=True, max_length=100)),
                ("damage_type", models.CharField(blank=True, max_length=100)),
                ("severity", models.CharField(
                    choices=[("minor","Minor"),("moderate","Moderate"),("major","Major"),("unknown","Unknown")],
                    default="unknown",
                    max_length=20,
                )),
                ("confidence", models.FloatField(default=0.0)),
                ("notes", models.TextField(blank=True)),
                ("raw_gemini_response", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("vehicle_image", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="damage_insights",
                    to="core.vehicleimage",
                )),
            ],
            options={"verbose_name": "Damage Insight", "verbose_name_plural": "Damage Insights", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="damageinsight",
            index=models.Index(fields=["vehicle_image"], name="di_vehicle_image_idx"),
        ),
        migrations.AddIndex(
            model_name="damageinsight",
            index=models.Index(fields=["severity"], name="di_severity_idx"),
        ),

        # ── ClaimEstimate ─────────────────────────────────────────────────────
        migrations.CreateModel(
            name="ClaimEstimate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("estimated_cost", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(default="INR", max_length=10)),
                ("calculation_notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("damage_insight", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="claim_estimates",
                    to="core.damageinsight",
                )),
            ],
            options={"verbose_name": "Claim Estimate", "verbose_name_plural": "Claim Estimates", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="claimestimate",
            index=models.Index(fields=["damage_insight"], name="ce_insight_idx"),
        ),
    ]
