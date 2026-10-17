# Deploying to Google Cloud Run

This guide deploys JobPortal to **Cloud Run** with:

| Piece | Service | Cost |
|---|---|---|
| App (Docker container) | Cloud Run | Free tier covers a portfolio site |
| Resumes | Cloud Storage (private bucket) | 5 GB free in `us-central1`, `us-east1`, `us-west1` |
| `SECRET_KEY`, database URL | Secret Manager | A few secrets free |
| PostgreSQL | [Neon](https://neon.tech) free tier | Free (Cloud SQL works too, but is paid) |
| Migrations / admin user | Cloud Run Jobs | Free tier |

Deploys are manual: run the tests, then one `gcloud run deploy` command.

> Google Cloud needs a billing account (card) even for free-tier usage. Set a
> budget alert (step 9) so you are never surprised. Free-tier limits change;
> check the current pricing pages.

Throughout this guide, replace:

- `PROJECT_ID` with your Google Cloud project ID
- `BUCKET` with a globally unique bucket name, e.g. `jobportal-resumes-anuj`
- Region `us-central1` is used everywhere so Cloud Storage stays in the free tier

---

## 1. Install and set up the gcloud CLI

Install: <https://cloud.google.com/sdk/docs/install> (on Ubuntu, the apt instructions are easiest).

```bash
gcloud auth login
gcloud projects create PROJECT_ID          # or pick an existing project
gcloud config set project PROJECT_ID
gcloud config set run/region us-central1
```

Link a billing account to the project in the console:
**Billing → My projects → PROJECT_ID → Change billing**.

Enable the APIs this deploy uses:

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
    artifactregistry.googleapis.com secretmanager.googleapis.com storage.googleapis.com
```

## 2. Create the database (Neon)

1. Sign up at <https://neon.tech> and create a project (pick a US region close to `us-central1`).
2. Copy the **connection string**. It looks like
   `postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require`

## 3. Create a service account for the app

The app runs as this account, which gets access only to its bucket and secrets.

```bash
gcloud iam service-accounts create jobportal-run --display-name "JobPortal Cloud Run"
SA=jobportal-run@PROJECT_ID.iam.gserviceaccount.com
```

## 4. Create the private resume bucket

```bash
gcloud storage buckets create gs://BUCKET \
    --location=us-central1 \
    --uniform-bucket-level-access \
    --public-access-prevention

gcloud storage buckets add-iam-policy-binding gs://BUCKET \
    --member="serviceAccount:$SA" --role=roles/storage.objectAdmin
```

The bucket is never public. Resumes are streamed through the app, which checks
that the viewer is the applicant or the employer who posted the job.

## 5. Store secrets in Secret Manager

```bash
# Django secret key (a fresh one, not the one in your local .env)
python3 -c "import secrets; print(secrets.token_urlsafe(50))" | tr -d '\n' | \
    gcloud secrets create django-secret-key --data-file=-

# Neon connection string from step 2 (keep the quotes)
printf '%s' 'postgresql://user:password@ep-xxx.neon.tech/neondb?sslmode=require' | \
    gcloud secrets create database-url --data-file=-

for s in django-secret-key database-url; do
  gcloud secrets add-iam-policy-binding $s \
      --member="serviceAccount:$SA" --role=roles/secretmanager.secretAccessor
done
```

## 6. Deploy the app

From the project root (where the `Dockerfile` is):

```bash
gcloud run deploy jobportal \
    --source . \
    --service-account "$SA" \
    --allow-unauthenticated \
    --max-instances 2 \
    --set-secrets "SECRET_KEY=django-secret-key:latest,DATABASE_URL=database-url:latest" \
    --set-env-vars "DEBUG=False,GS_BUCKET_NAME=BUCKET,ALLOWED_HOSTS=.run.app"
```

`--source .` uploads the code, Cloud Build builds the `Dockerfile`, and the image
is stored in Artifact Registry (say **yes** if asked to create a repository).
`--max-instances 2` caps how far it can scale, which caps cost.

When it finishes it prints the service URL, e.g. `https://jobportal-abc123-uc.a.run.app`.
Django needs that exact origin to accept form posts:

```bash
gcloud run services update jobportal \
    --update-env-vars "CSRF_TRUSTED_ORIGINS=https://jobportal-abc123-uc.a.run.app"
```

The site will show errors until the database tables exist. That's the next step.

## 7. Run migrations (Cloud Run Job)

Create a job that reuses the app's image and settings:

```bash
IMAGE=$(gcloud run services describe jobportal \
    --format='value(spec.template.spec.containers[0].image)')

gcloud run jobs create jobportal-manage \
    --image "$IMAGE" \
    --service-account "$SA" \
    --set-secrets "SECRET_KEY=django-secret-key:latest,DATABASE_URL=database-url:latest" \
    --set-env-vars "DEBUG=False,GS_BUCKET_NAME=BUCKET" \
    --command python \
    --args manage.py,migrate,--noinput

gcloud run jobs execute jobportal-manage --wait
```

## 8. Create an admin user

Reuse the same job with different arguments:

```bash
gcloud run jobs execute jobportal-manage --wait \
    --args manage.py,createsuperuser,--noinput \
    --update-env-vars "DJANGO_SUPERUSER_USERNAME=admin,DJANGO_SUPERUSER_EMAIL=you@example.com,DJANGO_SUPERUSER_PASSWORD=choose-a-temp-password"
```

The password is visible in the job execution's settings, so log in at
`/admin/` and change it right away.

Open the service URL. Sign up as an employer, post a job, then sign up as a
job seeker and apply with a PDF.

## 9. Set a budget alert (recommended)

Console → **Billing → Budgets & alerts → Create budget**, e.g. ₹100 with alerts
at 50% / 90% / 100%. Alerts email you; they don't stop services.

---

## Deploying an update

```bash
pytest                                   # make sure everything passes
gcloud run deploy jobportal --source .   # keeps the existing settings and secrets
```

If the update includes new migrations, point the job at the new image and run it:

```bash
IMAGE=$(gcloud run services describe jobportal \
    --format='value(spec.template.spec.containers[0].image)')
gcloud run jobs update jobportal-manage --image "$IMAGE"
gcloud run jobs execute jobportal-manage --wait
```

## Viewing logs

```bash
gcloud run services logs read jobportal --limit 50
```

Or in the console: **Cloud Run → jobportal → Logs**.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Bad Request (400)` | `ALLOWED_HOSTS` doesn't match the URL. `.run.app` covers the default URL; add custom domains. |
| `403 CSRF verification failed` on forms | `CSRF_TRUSTED_ORIGINS` must be the exact `https://...` service URL (step 6). |
| `500` right after the first deploy | Migrations haven't run yet (step 7). Check logs. |
| Resume upload fails with a permission error | The service account lacks `roles/storage.objectAdmin` on the bucket (step 4), or the service isn't using `--service-account "$SA"`. |
| Build fails with a permission error | New projects sometimes need the Cloud Build service account to have access. The error message names the missing role; grant it in **IAM**. |
| First request is slow | Cloud Run scales to zero when idle and cold-starts on the next visit. That's expected on the free tier. |

## Removing everything

```bash
gcloud run services delete jobportal
gcloud run jobs delete jobportal-manage
gcloud storage rm --recursive gs://BUCKET
gcloud secrets delete django-secret-key
gcloud secrets delete database-url
gcloud artifacts repositories delete cloud-run-source-deploy --location us-central1
```

Or delete the whole project: `gcloud projects delete PROJECT_ID`.
