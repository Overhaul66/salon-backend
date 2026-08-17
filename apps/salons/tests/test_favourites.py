import pytest
import datetime
from rest_framework.test import APIClient
from apps.users.models import CustomUser
from apps.users.services import register_user
from apps.salons.models import SalonFavourite
from apps.salons.services import create_salon

@pytest.mark.django_db
class TestSalonFavourites:
    @pytest.fixture(autouse=True)
    def setup(self):
        manager_user = register_user(
            email="fmanager@test.com",
            password="password123",
            role="SALON_MANAGER",
            phone="4444000001"
        )
        self.manager = manager_user.manager_profile

        self.salon1 = create_salon(
            manager=self.manager,
            name="Fav Salon One",
            phone="555-1001",
            address="1 Fav St",
            city="FavCity",
            country="TestCountry",
            opening_time=datetime.time(9, 0),
            closing_time=datetime.time(18, 0)
        )
        self.salon2 = create_salon(
            manager=self.manager,
            name="Fav Salon Two",
            phone="555-1002",
            address="2 Fav St",
            city="FavCity",
            country="TestCountry",
            opening_time=datetime.time(9, 0),
            closing_time=datetime.time(18, 0)
        )

        cust_u = register_user(
            email="fcust@test.com",
            password="password123",
            role="CUSTOMER",
            phone="4444000002"
        )
        self.customer = cust_u.customer_profile

        self.client = APIClient()
        self.client.force_authenticate(user=cust_u)

    def test_customer_adds_favourite(self):
        res = self.client.post(f"/api/salons/{self.salon1.id}/favourite/")
        assert res.status_code == 200
        assert res.data["is_favourited"] is True
        assert SalonFavourite.objects.filter(
            customer=self.customer, salon=self.salon1
        ).count() == 1

    def test_duplicate_favourite_is_idempotent(self):
        self.client.post(f"/api/salons/{self.salon1.id}/favourite/")
        res = self.client.post(f"/api/salons/{self.salon1.id}/favourite/")
        assert res.status_code == 200
        assert SalonFavourite.objects.filter(
            customer=self.customer, salon=self.salon1
        ).count() == 1

    def test_unfavourite_removes(self):
        self.client.post(f"/api/salons/{self.salon1.id}/favourite/")
        res = self.client.delete(f"/api/salons/{self.salon1.id}/unfavourite/")
        assert res.status_code == 200
        assert res.data["is_favourited"] is False
        assert SalonFavourite.objects.filter(
            customer=self.customer, salon=self.salon1
        ).count() == 0

    def test_favourites_list_returns_only_mine(self):
        self.client.post(f"/api/salons/{self.salon1.id}/favourite/")
        other_cust_u = register_user(
            email="fcust2@test.com",
            password="password123",
            role="CUSTOMER",
            phone="4444000003"
        )
        other_client = APIClient()
        other_client.force_authenticate(user=other_cust_u)
        other_client.post(f"/api/salons/{self.salon2.id}/favourite/")

        res = self.client.get("/api/salons/favourites/")
        assert res.status_code == 200
        ids = [s["id"] for s in res.data["results"]]
        assert str(self.salon1.id) in ids
        assert str(self.salon2.id) not in ids

    def test_non_customer_cannot_favourite(self):
        manager_client = APIClient()
        manager_client.force_authenticate(
            user=CustomUser.objects.get(email="fmanager@test.com")
        )
        res = manager_client.post(f"/api/salons/{self.salon1.id}/favourite/")
        assert res.status_code == 403

    def test_is_favourited_flag_in_salon_detail(self):
        self.client.post(f"/api/salons/{self.salon1.id}/favourite/")
        res = self.client.get(f"/api/salons/{self.salon1.id}/")
        assert res.status_code == 200
        assert res.data["is_favourited"] is True

    def test_anonymous_user_gets_false_flag(self):
        anon = APIClient()
        res = anon.get(f"/api/salons/{self.salon1.id}/")
        assert res.status_code == 200
        assert res.data["is_favourited"] is False