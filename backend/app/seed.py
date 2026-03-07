"""Seed the database with a test store and demo menu for development."""

from __future__ import annotations

from decimal import Decimal

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.menu import Menu
from app.models.menu_item import MenuItem
from app.models.menu_menu_item import MenuMenuItem
from app.models.store import Store

TEST_STORE_EMAIL = "test@example.com"

DEMO_MENU_ITEMS = [
    {
        "name": "Kung Pao Chicken",
        "alias_name": "宫保鸡丁",
        "category": "Main",
        "price": Decimal("14.99"),
        "price_small": Decimal("10.99"),
        "price_medium": Decimal("14.99"),
        "price_large": Decimal("18.99"),
        "ingredient": "chicken, peanuts, dried chili peppers, Sichuan peppercorn, scallion, ginger, garlic",
        "note": "Spicy. Contains peanuts.",
        "tags": ["spicy", "chicken", "popular"],
    },
    {
        "name": "Mapo Tofu",
        "alias_name": "麻婆豆腐",
        "category": "Main",
        "price": Decimal("12.99"),
        "price_small": Decimal("8.99"),
        "price_medium": Decimal("12.99"),
        "price_large": Decimal("16.99"),
        "ingredient": "silken tofu, ground pork, doubanjiang, Sichuan peppercorn, scallion",
        "note": "Spicy and numbing. Can be made vegetarian (no pork).",
        "tags": ["spicy", "tofu", "popular"],
    },
    {
        "name": "Sweet and Sour Pork",
        "alias_name": "糖醋里脊",
        "category": "Main",
        "price": Decimal("15.99"),
        "price_small": Decimal("11.99"),
        "price_medium": Decimal("15.99"),
        "price_large": Decimal("19.99"),
        "ingredient": "pork tenderloin, pineapple, bell pepper, onion, ketchup, rice vinegar, sugar",
        "note": None,
        "tags": ["pork", "sweet"],
    },
    {
        "name": "Beef with Broccoli",
        "alias_name": "西兰花牛肉",
        "category": "Main",
        "price": Decimal("15.99"),
        "price_small": Decimal("11.99"),
        "price_medium": Decimal("15.99"),
        "price_large": Decimal("19.99"),
        "ingredient": "flank steak, broccoli, garlic, oyster sauce, soy sauce, sesame oil",
        "note": None,
        "tags": ["beef", "popular"],
    },
    {
        "name": "General Tso's Chicken",
        "alias_name": "左宗棠鸡",
        "category": "Main",
        "price": Decimal("14.99"),
        "price_small": Decimal("10.99"),
        "price_medium": Decimal("14.99"),
        "price_large": Decimal("18.99"),
        "ingredient": "chicken thigh, dried chili, garlic, ginger, soy sauce, sugar, rice vinegar",
        "note": "Mildly spicy. Crispy battered chicken.",
        "tags": ["spicy", "chicken", "fried"],
    },
    {
        "name": "Hot and Sour Soup",
        "alias_name": "酸辣汤",
        "category": "Soup",
        "price": Decimal("7.99"),
        "price_small": Decimal("5.99"),
        "price_medium": Decimal("7.99"),
        "price_large": Decimal("10.99"),
        "ingredient": "tofu, wood ear mushroom, bamboo shoot, egg, white pepper, rice vinegar",
        "note": "Spicy. Contains egg.",
        "tags": ["soup", "spicy"],
    },
    {
        "name": "Wonton Soup",
        "alias_name": "馄饨汤",
        "category": "Soup",
        "price": Decimal("8.99"),
        "price_small": Decimal("6.99"),
        "price_medium": Decimal("8.99"),
        "price_large": Decimal("11.99"),
        "ingredient": "pork and shrimp wontons, chicken broth, bok choy, scallion",
        "note": "Contains shellfish.",
        "tags": ["soup"],
    },
    {
        "name": "Fried Rice",
        "alias_name": "炒饭",
        "category": "Rice & Noodle",
        "price": Decimal("11.99"),
        "price_small": Decimal("8.99"),
        "price_medium": Decimal("11.99"),
        "price_large": Decimal("14.99"),
        "ingredient": "jasmine rice, egg, carrot, peas, scallion, soy sauce",
        "note": "Add chicken +$2, shrimp +$3, beef +$3.",
        "tags": ["rice", "popular"],
    },
    {
        "name": "Chow Mein",
        "alias_name": "炒面",
        "category": "Rice & Noodle",
        "price": Decimal("12.99"),
        "price_small": Decimal("9.99"),
        "price_medium": Decimal("12.99"),
        "price_large": Decimal("15.99"),
        "ingredient": "egg noodles, cabbage, carrot, bean sprout, scallion, soy sauce, sesame oil",
        "note": "Add chicken +$2, shrimp +$3, beef +$3.",
        "tags": ["noodle", "popular"],
    },
    {
        "name": "Dan Dan Noodles",
        "alias_name": "担担面",
        "category": "Rice & Noodle",
        "price": Decimal("13.99"),
        "price_small": Decimal("9.99"),
        "price_medium": Decimal("13.99"),
        "price_large": Decimal("16.99"),
        "ingredient": "wheat noodles, ground pork, preserved mustard greens, Sichuan peppercorn, chili oil, sesame paste",
        "note": "Spicy and numbing.",
        "tags": ["noodle", "spicy"],
    },
    {
        "name": "Spring Rolls (4 pcs)",
        "alias_name": "春卷",
        "category": "Appetizer",
        "price": Decimal("6.99"),
        "ingredient": "cabbage, carrot, glass noodle, spring roll wrapper",
        "note": "Vegetarian. Crispy fried.",
        "tags": ["appetizer", "vegetarian", "fried"],
    },
    {
        "name": "Pork Dumplings (8 pcs)",
        "alias_name": "猪肉饺子",
        "category": "Appetizer",
        "price": Decimal("9.99"),
        "ingredient": "ground pork, napa cabbage, ginger, scallion, sesame oil",
        "note": "Steamed or pan-fried. Served with soy-vinegar dipping sauce.",
        "tags": ["appetizer", "dumpling", "popular"],
    },
    {
        "name": "Peking Duck",
        "alias_name": "北京烤鸭",
        "category": "Specialty",
        "price": Decimal("38.99"),
        "ingredient": "whole duck, hoisin sauce, scallion, cucumber, thin pancakes",
        "note": "Serves 2-3 people. Please allow 30 min prep time.",
        "tags": ["duck", "specialty"],
    },
    {
        "name": "Steamed Fish with Ginger and Scallion",
        "alias_name": "清蒸鱼",
        "category": "Specialty",
        "price": Decimal("22.99"),
        "ingredient": "whole sea bass, ginger, scallion, soy sauce, sesame oil",
        "note": "Light and healthy. Ask server for today's fresh catch.",
        "tags": ["seafood", "steamed", "healthy"],
    },
    {
        "name": "Stir-fried Green Beans",
        "alias_name": "干煸四季豆",
        "category": "Vegetable",
        "price": Decimal("11.99"),
        "price_small": Decimal("8.99"),
        "price_medium": Decimal("11.99"),
        "price_large": Decimal("14.99"),
        "ingredient": "green beans, ground pork, dried chili, garlic, Sichuan peppercorn",
        "note": "Mildly spicy. Can be made vegetarian.",
        "tags": ["vegetable", "spicy"],
    },
    {
        "name": "Egg Drop Soup",
        "alias_name": "蛋花汤",
        "category": "Soup",
        "price": Decimal("6.99"),
        "price_small": Decimal("4.99"),
        "price_medium": Decimal("6.99"),
        "price_large": Decimal("9.99"),
        "ingredient": "chicken broth, egg, corn starch, scallion, white pepper",
        "note": "Contains egg. Mild flavor.",
        "tags": ["soup", "mild"],
    },
    {
        "name": "Jasmine Tea",
        "alias_name": "茉莉花茶",
        "category": "Beverage",
        "price": Decimal("2.99"),
        "ingredient": None,
        "note": "Pot serves 2-3 cups. Free refills.",
        "tags": ["beverage", "tea"],
    },
    {
        "name": "Mango Pudding",
        "alias_name": "芒果布丁",
        "category": "Dessert",
        "price": Decimal("5.99"),
        "ingredient": "mango, coconut milk, gelatin, sugar",
        "note": None,
        "tags": ["dessert"],
    },
]


def seed() -> None:
    db = SessionLocal()
    try:
        # --- Store ---
        store = db.query(Store).filter(Store.email == TEST_STORE_EMAIL).first()
        if not store:
            store = Store(
                name="Test Kitchen",
                email=TEST_STORE_EMAIL,
                password_hash=hash_password("testpass123"),
                phone="+1-555-0100",
                address_line1="123 Main St",
                city="San Francisco",
                state="CA",
                postal_code="94102",
                country="US",
                allow_pickup=True,
                allow_delivery=True,
            )
            db.add(store)
            db.flush()
            print(f"Seeded test store '{store.name}' ({TEST_STORE_EMAIL}).")
        else:
            print(f"Seed: store '{store.name}' ({TEST_STORE_EMAIL}) already exists, skipping.")

        # --- Menu ---
        existing_menu = (
            db.query(Menu)
            .filter(Menu.store_id == store.id, Menu.name == "Golden Dragon Menu")
            .first()
        )
        if existing_menu:
            print(f"Seed: menu '{existing_menu.name}' already exists, skipping.")
        else:
            menu = Menu(
                store_id=store.id,
                name="Golden Dragon Menu",
                active=True,
                version=1,
            )
            db.add(menu)
            db.flush()

            for item_data in DEMO_MENU_ITEMS:
                item = MenuItem(
                    store_id=store.id,
                    name=item_data["name"],
                    alias_name=item_data["alias_name"],
                    category=item_data.get("category"),
                    price=item_data["price"],
                    price_small=item_data.get("price_small"),
                    price_medium=item_data.get("price_medium"),
                    price_large=item_data.get("price_large"),
                    ingredient=item_data["ingredient"],
                    note=item_data["note"],
                    tags=item_data["tags"],
                    availability=True,
                )
                db.add(item)
                db.flush()
                db.add(MenuMenuItem(menu_id=menu.id, menu_item_id=item.id))

            db.commit()
            print(f"Seeded menu '{menu.name}' with {len(DEMO_MENU_ITEMS)} items.")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
