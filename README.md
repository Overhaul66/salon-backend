# Salon Connect — Backend Guide

A detailed guide to the **Salon Connect** Django/DRF backend: how accounts work (signup → login → profile), how salons and services are created, how managers create employees, and how the booking engine works — including every safeguard that prevents bad bookings.

- **Stack:** Django 5.2 · Django REST Framework 3.16 · PostgreSQL · SimpleJWT · drf-spectacular (OpenAPI) · django-storages + AWS S3 (images)
- **Base URL (local dev):** `http://localhost:8000`
- **Interactive API docs:** `http://localhost:8000/api/docs/` (Swagger) · `http://localhost:8000/api/redoc/`
- **OpenAPI schema:** `http://localhost:8000/api/schema/`
- **Health check:** `http://localhost:8000/health/`

---

## 1. Project layout

```
salon/
├── config/            # settings.py, urls.py (root routing)
├── apps/
│   ├── users/         # accounts, roles, auth (JWT), profiles, passwords
│   ├── salons/        # salons, services, catalog, business hours, images, favourites
│   ├── employees/     # manager-only employee management (create/update/reset password)
│   ├── scheduling/    # availability engine (AVAILABLE/BOOKED/BREAK/LEAVE slots)
│   ├── appointments/  # booking engine, status lifecycle, manager dashboard
│   ├── notifications/ # in-app notifications
│   └── common/        # shared models, Base64ImageField, seed commands
```

Each app follows the same layering: **`views.py`** (HTTP + permissions) → **`serializers.py`** (validation) → **`services.py`** (business rules) → **`models.py`** (data).

### Running it

```bash
docker compose up -d --build web            # start backend (Docker Desktop)
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_ghana    # or: seed_data — demo data + accounts
```

Seeded demo accounts are listed in `SEED_ACCOUNTS_GHANA.md` (all use password `password123`).

---

## 2. Roles & accounts

Every account is a `CustomUser` with one of three roles. Creating the user automatically creates the matching profile row (via a Django signal):

| Role | Profile created | What they can do |
|---|---|---|
| `CUSTOMER` | `Customer` | Browse salons, book/cancel own appointments, favourite salons |
| `SALON_MANAGER` | `SalonManager` | Create/manage **one** salon, its services & hours, create employees, confirm/decline bookings, view dashboard |
| `SALON_EMPLOYEE` | `SalonEmployee` | View own appointments, update their status (start/complete/no-show) |

Django superusers (`is_staff`/`is_superuser`) can see and manage everything.

## 3. Authentication (signup → login → refresh → logout)

Auth uses **JWT** (`djangorestframework-simplejwt`). Login/register return an `access` token (short-lived) and a `refresh` token. Every authenticated request sends:

```
Authorization: Bearer <access_token>
```

### 3.1 Sign up — `POST /api/auth/register/`

Open to anyone. Pass a `role` to decide the account type. A profile picture (optional) is sent as a **base64 data string** and is stored on AWS S3; the API responds with the public S3 URL.

```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "kwesi@example.com",
    "password": "Str0ngPass!23",
    "first_name": "Kwesi",
    "last_name": "Owusu",
    "phone": "+233241234567",
    "role": "CUSTOMER",
    "gender": "MALE",
    "date_of_birth": "1995-04-12",
    "profile_picture": "data:image/png;base64,iVBORw0KGgo..."
  }'
```

**201 response:**

```json
{
  "user": {
    "id": "9f1c…",
    "email": "kwesi@example.com",
    "first_name": "Kwesi",
    "role": "CUSTOMER",
    "profile_picture": "https://salon-momo.s3.amazonaws.com/profile_pictures/abc123.png",
    "is_active": true
  },
  "tokens": {
    "refresh": "eyJhbGciOi…",
    "access": "eyJhbGciOi…"
  }
}
```

**Signup safeguards**

- Password must be **≥ 8 characters** (`min_length=8`, plus Django's password validators).
- **Duplicate email** → `400` `"A user with this email already exists."` (checked in serializer *and* service layer).
- **Duplicate phone** → `400` `"A user with this phone number already exists."`.
- **Invalid role** → `400` `"Invalid role selected."`. Only the three roles above can self-register — employees are normally created *by managers* (§5).

### 3.2 Log in — `POST /api/auth/login/`

```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{ "email": "kwesi@example.com", "password": "Str0ngPass!23" }'
```

**200 response** — the full `user` object is included so clients can bootstrap immediately:

```json
{
  "refresh": "eyJhbGciOi…",
  "access": "eyJhbGciOi…",
  "user": { "id": "9f1c…", "email": "kwesi@example.com", "role": "CUSTOMER" }
}
```

Wrong credentials → `401` `{"detail": "No active account found with the given credentials"}`.

### 3.3 Refresh / logout — `POST /api/auth/refresh/`, `POST /api/auth/logout/`

```bash
# exchange the refresh token for a new access token
curl -X POST http://localhost:8000/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{ "refresh": "eyJhbGciOi…" }'

# logout blacklists the refresh token so it can never be reused
curl -X POST http://localhost:8000/api/auth/logout/ \
  -H "Authorization: Bearer <access>" -H "Content-Type: application/json" \
  -d '{ "refresh": "eyJhbGciOi…" }'
```

Invalid/expired refresh tokens → `400 {"detail": "Token is invalid or expired."}`.

### 3.4 Profile — `GET|PATCH /api/auth/me/`

```bash
curl http://localhost:8000/api/auth/me/ -H "Authorization: Bearer <access>"

curl -X PATCH http://localhost:8000/api/auth/me/ \
  -H "Authorization: Bearer <access>" -H "Content-Type: application/json" \
  -d '{ "first_name": "Kwesi", "profile_picture": "data:image/jpeg;base64,…" }'
```

Only `first_name`, `last_name`, `phone`, `profile_picture` are writable — `role`, `email`, `is_verified` are read-only.

### 3.5 Password management

| Endpoint | Body | Notes |
|---|---|---|
| `POST /api/auth/password/change/` | `old_password`, `new_password` | Authenticated; verifies old password first. |
| `POST /api/auth/password/reset/` | `email` | Returns `uidb64` + `token` (in response for testing; wire to email in production). Unknown emails get the same response — **prevents account enumeration**. |
| `POST /api/auth/password/reset/confirm/` | `uidb64`, `token`, `new_password` | Invalid/expired token → `400 "Invalid or expired reset token."` |

## 4. Salons & services

### 4.1 Browse salons — `GET /api/salons/`

Public (no auth). Supports filtering, search and ordering:

```bash
curl "http://localhost:8000/api/salons/?city=Accra&service=Braids&ordering=-rating"
```

Filters: `city`, `gender_type` (`UNISEX`/`MEN_ONLY`/`WOMEN_ONLY`), `status`, full-text `search` on name/description/city, plus `service`, `rating`, and geo `lat`/`lon` params handled by `list_salons`.

### 4.2 Create a salon — `POST /api/salons/`

**Managers only** (`IsAuthenticated` + `IsSalonManager`). A manager owns **exactly one salon** — attempting a second is rejected:

```bash
curl -X POST http://localhost:8000/api/salons/ \
  -H "Authorization: Bearer <manager_access>" -H "Content-Type: application/json" \
  -d '{
    "name": "CBK Beauty Flagship Salon",
    "phone": "+233302741001",
    "address": "31 Kanda Highway",
    "city": "Accra",
    "country": "Ghana",
    "opening_time": "08:30:00",
    "closing_time": "19:00:00",
    "gender_type": "UNISEX",
    "logo": "data:image/png;base64,…",
    "cover_image": "data:image/png;base64,…",
    "business_hours": [
      { "weekday": 0, "opening_time": "08:00", "closing_time": "19:00", "is_closed": false },
      { "weekday": 6, "opening_time": "00:00", "closing_time": "00:00", "is_closed": true }
    ]
  }'
```

**Safeguards**
- Only `SALON_MANAGER` users can create/delete; a manager already owning a salon gets `403 "You already manage a salon."`.
- `slug` is auto-generated from the name and de-duplicated (`cbk-beauty-flagship-salon`, `-1`, `-2`, …).
- If `business_hours` is omitted, default hours (open every day, salon's opening/closing times) are auto-created for all 7 weekdays.
- `logo` / `cover_image` are base64 uploads → stored on **AWS S3**; the response returns public S3 URLs.

Other salon endpoints: `GET /api/salons/{id}/`, `GET|PATCH|DELETE /api/salons/me/` (manager's own salon), plus `salon-images`, `business-hours`, and `favourites` actions on the viewset. Updates are restricted by `IsSalonOwnerOrReadOnly` — only the owning manager can edit.

### 4.3 Services

- **Catalog** (global templates): `GET /api/service-catalog/` — public, filterable by `category`.
- **Salon services** (what a salon actually offers, with its own price/duration): `GET|POST /api/services/`, filterable by `salon`. Managers attach services to their salon via `create_salon_service` — either custom values or copied from a `catalog_item` (duplicate catalog items per salon are rejected).

```json
{
  "id": "b52…",
  "salon": "a63f…",
  "name": "Signature Braids",
  "duration_minutes": 120,
  "price": "250.00",
  "is_active": true
}
```

`duration_minutes` and `is_active` feed directly into the booking engine (§6) — inactive services cannot be booked (`is_active: true` filter on the customer booking screen).

## 5. Employee creation (manager-only)

Managers create employee accounts under their salon via the `employees` endpoints (`IsAuthenticated` + `IsSalonManager` — a customer or employee calling this gets `403`).

### 5.1 Create an employee — `POST /api/employees/`

```bash
curl -X POST http://localhost:8000/api/employees/ \
  -H "Authorization: Bearer <manager_access>" -H "Content-Type: application/json" \
  -d '{
    "email": "efua.stylist@salon.com",
    "password": "TempPass!234",
    "first_name": "Efua",
    "last_name": "Boateng",
    "phone": "+233245110011",
    "salon": "a63fa029-6401-4fbf-808d-ad760fa91b26",
    "bio": "Braids, weaves and precision cuts.",
    "services": ["b52e…", "c91a…"],
    "profile_picture": "data:image/jpeg;base64,…"
  }'
```

**201 response** (the manager immediately sees the new employee in their team list):

```json
{
  "id": "77aa…",
  "user": { "email": "efua.stylist@salon.com", "first_name": "Efua", "role": "SALON_EMPLOYEE" },
  "salon": "a63f…",
  "salon_name": "CBK Beauty Flagship Salon",
  "position": "",
  "bio": "Braids, weaves and precision cuts.",
  "is_available": true
}
```

**Safeguards (in `employees/services.py`, wrapped in `@transaction.atomic`)**
1. **Ownership check** — `check_manager_owns_salon` raises `"You do not own this salon."` if the `salon` in the payload is not the manager's own salon. You cannot seed employees into someone else's salon.
2. **Service–salon consistency** — every `services` id must belong to *that* salon: `"All selected services must belong to the employee's salon."` This guarantees the booking engine only ever matches employees to services they truly perform.
3. **Atomic creation** — the user account + employee profile + service assignments all commit together or not at all (no half-created employees).
4. Duplicate email/phone are rejected by the shared `register_user` rules (§3.1).

### 5.2 Manage employees

| Action | Endpoint | Notes |
|---|---|---|
| List my team | `GET /api/employees/` | Scoped to the manager's salon (`list_employees_for_manager`); filterable by `is_available`. |
| Update | `PATCH /api/employees/{id}/` | Name/phone, `position`, `bio`, `is_available`, `employment_date`, reassign `services` (same salon-only check applies). |
| Deactivate | `PATCH /api/employees/{id}/` `{"user": {"is_active": false}}` | Blocked from logging in; `is_available: false` also removes them from booking rotation. |
| Reset password | `POST /api/employees/{id}/reset-password/` `{"password": "NewPass!234"}` | Manager-only, ownership-checked. |

**Why it matters for booking:** an employee only appears in the auto-assignment pool (§6) if they are `is_available=True` and their `services` M2M contains the requested service.

## 6. Booking management (the engine)

Customers book; the system **auto-assigns the best available employee** and validates the slot against many rules. Booking is **customer-only**: `POST /api/appointments/` from any other role returns `403 "Only customers can book appointments."`.

### 6.1 Book an appointment — `POST /api/appointments/`

```bash
curl -X POST http://localhost:8000/api/appointments/ \
  -H "Authorization: Bearer <customer_access>" -H "Content-Type: application/json" \
  -d '{
    "salon": "a63fa029-6401-4fbf-808d-ad760fa91b26",
    "service": "b52e1111-2222-3333-4444-555566667777",
    "appointment_date": "2026-09-01",
    "start_time": "11:00:00",
    "booking_notes": "Knotless braids, medium length please."
  }'
```

Note: the customer does **not** pick an employee — `create_appointment` finds one (see safeguards below). The end time is computed from the service duration (`start_time + duration_minutes`).

**201 response:**

```json
{
  "id": "3f8d…",
  "customer": { "id": "9f1c…", "email": "kwesi@example.com" },
  "salon": "a63f…",
  "employee": "77aa…",
  "service": "b52e…",
  "appointment_date": "2026-09-01",
  "start_time": "11:00:00",
  "end_time": "13:00:00",
  "status": "PENDING",
  "booking_notes": "Knotless braids, medium length please."
}
```

### 6.2 Booking safeguards (all enforced before an appointment is created)

`create_appointment` runs inside `@transaction.atomic`, and delegates slot validation to `find_available_employee`. The checks, in order:

1. **Salon must be open** — the weekday's `BusinessHours` row is checked; if `is_closed` → `"The salon is closed on this day."` If no hours row exists, the salon's default `opening_time`/`closing_time` are used.
2. **Inside business hours** — the computed *end* time (not just the start) must fit: `"The requested time is outside salon business hours (08:30:00 - 19:00:00)."` A 120-minute service requested at 18:00 is rejected.
3. **Someone can actually do the service** — eligible employees are `salon`, `is_available=True`, and have the service in their `services` M2M. None? → `"No employee at this salon currently performs this service."`
4. **Availability slots are generated on demand** — `generate_employee_availability(employee, date)` lazily creates the day's `AVAILABLE` slot from business hours, so future dates always have a schedule without a cron job.
5. **Blocked schedules are skipped** — employees with `BREAK`, `LEAVE`, or `BOOKED` availability rows overlapping the requested window (`start < existing_end AND end > existing_start`) are excluded.
6. **No double-booking** — employees with an overlapping appointment in an active status (`PENDING`, `CONFIRMED`, `IN_PROGRESS`) are excluded. Overlap uses the same interval test, so back-to-back bookings (13:00–15:00 after 11:00–13:00) are allowed.
7. **Clear error when it's genuinely busy** — if exactly one employee performs the service: `"The stylist who performs this service is busy at that time. Please choose another date or time."`; otherwise `"No employees are available at this date and time."`
8. **Workload balancing** — among the remaining candidates, the employee with the **fewest appointments that day** wins, spreading work evenly across the team.
9. **Slot is locked immediately** — on success a `BOOKED` `EmployeeAvailability` row is created for the exact window, so the next overlapping request is rejected at step 5.
10. **Everything or nothing** — the whole operation is one DB transaction: appointment row + BOOKED slot are committed together.

**Example rejections (400):**

```json
{ "detail": "The salon is closed on this day." }
{ "detail": "The requested time is outside salon business hours (09:00:00 - 18:30:00)." }
{ "detail": "The stylist who performs this service is busy at that time. Please choose another date or time." }
```

## 7. Appointment lifecycle

```
PENDING ──► CONFIRMED ──► IN_PROGRESS ──► COMPLETED
   │              │
   │              └──► DECLINED
   ├──► CANCELLED (customer or manager)
   └──► (any active state) ──► NO_SHOW (employee)
```

- New bookings start as **`PENDING`**.
- **Employees** update the status of appointments assigned to them: `PATCH /api/my/appointments/{id}/status/` with `{"status": "CONFIRMED" | "IN_PROGRESS" | "COMPLETED" | "DECLINED" | "NO_SHOW"}`.
- **Cancelling** — customer or manager: `POST /api/appointments/{id}/cancel/` with `{"cancel_reason": "…"}`
- **Safeguards on transitions:**
  - Invalid target status → `400 "Invalid status transition to …"`.
  - Cancelled/declined appointments are **frozen** — `"Cannot change the status of a cancelled or declined appointment."`
  - You cannot cancel a `COMPLETED` or already-`CANCELLED` appointment.
  - `COMPLETED`, `DECLINED`, `CANCELLED`, and `NO_SHOW` all **delete the `BOOKED` availability row**, releasing the time slot for someone else.

### Notifications

Every meaningful transition fires in-app notifications (`apps/notifications`): booking (customer + assigned employee + manager), confirmation, decline, completion, and cancellation — e.g. *"Your appointment at CBK Beauty Flagship Salon for Signature Braids has been booked on 2026-09-01 at 11:00:00."*

## 8. Who can see which appointments (access control)

`AppointmentAccessPermission` + role-scoped querysets in `AppointmentViewSet.get_queryset()`:

| Role | Sees |
|---|---|
| `CUSTOMER` | Only their own bookings |
| `SALON_EMPLOYEE` | Only appointments assigned to them |
| `SALON_MANAGER` | All appointments at their salon(s) |
| Superuser | Everything |

The manager also gets `GET /api/manager/dashboard/` — today's pending/confirmed/completed counts, revenue, salon count, and recent appointments. Employees get `GET /api/my/appointments/?date=YYYY-MM-DD` for their day sheet.

## 9. Endpoint reference

| Area | Method & path | Auth |
|---|---|---|
| Register | `POST /api/auth/register/` | public |
| Login | `POST /api/auth/login/` | public |
| Refresh / logout | `POST /api/auth/refresh/` · `POST /api/auth/logout/` | public / authed |
| Profile | `GET|PATCH /api/auth/me/` | authed |
| Passwords | `POST /api/auth/password/change/` · `…/reset/` · `…/reset/confirm/` | mixed |
| Salons | `GET /api/salons/` · `GET /api/salons/{id}/` | public |
| Create/manage salon | `POST /api/salons/` · `GET|PATCH|DELETE /api/salons/me/` | manager |
| Service catalog | `GET /api/service-catalog/` | public |
| Salon services | `GET|POST /api/services/` (filter `?salon=`) | public / manager |
| Employees | `GET|POST /api/employees/` · `PATCH /api/employees/{id}/` · `POST /api/employees/{id}/reset-password/` | manager |
| Book | `POST /api/appointments/` | customer |
| My bookings | `GET /api/appointments/` (role-scoped, filters `?salon=&status=&appointment_date=`) | authed |
| Cancel | `POST /api/appointments/{id}/cancel/` | customer/manager (owner) |
| Employee day sheet | `GET /api/my/appointments/?date=` | employee |
| Employee status update | `PATCH /api/my/appointments/{id}/status/` | employee |
| Manager dashboard | `GET /api/manager/dashboard/` | manager |

## 10. Images (base64 in, S3 URL out)

All image fields (`profile_picture`, salon `logo`/`cover_image`, gallery images, employee photos) accept **base64 data strings** via `apps/common/fields.Base64ImageField`. The file is written through Django's default storage → **AWS S3** (`django-storages` + `boto3`, region `eu-north-1`), and every API response exposes a public URL like:

```
https://salon-momo.s3.amazonaws.com/profile_pictures/abc123.png
```

Credentials live only in the backend `.env` — never in the frontend bundle. Without AWS env vars set, storage transparently falls back to the local filesystem (dev/CI).

## 11. Testing

```bash
docker compose exec web python -m pytest apps/appointments/tests -q   # booking engine tests
docker compose exec web python manage.py check                        # config sanity
docker compose exec web python -m pytest apps/common/tests/test_image_uploads.py -q  # S3 upload flow
```


