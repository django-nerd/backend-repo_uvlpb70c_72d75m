import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product

app = FastAPI(title="Hardware Store API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProductCreate(Product):
    pass


class ProductOut(Product):
    id: str


@app.get("/")
def read_root():
    return {"message": "Hardware Store Backend Running"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Check environment variables
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# Utility to convert Mongo docs

def serialize_product(doc) -> ProductOut:
    return ProductOut(
        id=str(doc.get("_id")),
        title=doc.get("title"),
        description=doc.get("description"),
        price=float(doc.get("price", 0)),
        category=doc.get("category"),
        in_stock=bool(doc.get("in_stock", True)),
        image_url=doc.get("image_url"),
        brand=doc.get("brand"),
    )


@app.get("/api/products", response_model=List[ProductOut])
def list_products(
    q: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100)
):
    filters = {}
    if q:
        filters["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"brand": {"$regex": q, "$options": "i"}},
        ]
    if category:
        filters["category"] = category

    docs = get_documents("product", filters, limit)
    return [serialize_product(d) for d in docs]


@app.post("/api/products", response_model=str)
def create_product(payload: ProductCreate):
    new_id = create_document("product", payload)
    return new_id


@app.get("/api/products/{product_id}", response_model=ProductOut)
def get_product(product_id: str):
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")

    doc = db["product"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return serialize_product(doc)


@app.post("/api/seed")
def seed_products():
    """Insert a curated set of example products if they don't already exist.
    Returns number of products inserted.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")

    sample = [
        {
            "title": "Cordless Drill Driver 20V (2 Batteries)",
            "description": "Compact 20V drill/driver with 2x 2.0Ah batteries, charger, and case.",
            "price": 129.99,
            "category": "power-tools",
            "in_stock": True,
            "image_url": "https://images.unsplash.com/photo-1604671801908-6df44230996e?q=80&w=1200&auto=format&fit=crop",
            "brand": "ToolPro"
        },
        {
            "title": "Brushless Impact Driver 18V",
            "description": "High‑torque brushless impact driver, variable speed, belt clip included.",
            "price": 149.0,
            "category": "power-tools",
            "in_stock": True,
            "image_url": "https://images.unsplash.com/photo-1605146768851-eda79da39894?q=80&w=1200&auto=format&fit=crop",
            "brand": "VoltMax"
        },
        {
            "title": "Claw Hammer 16oz Fiberglass",
            "description": "Durable fiberglass handle with non‑slip grip and polished steel head.",
            "price": 19.99,
            "category": "hand-tools",
            "in_stock": True,
            "image_url": "https://images.unsplash.com/photo-1581092921461-eab62e97a14f?q=80&w=1200&auto=format&fit=crop",
            "brand": "ForgeMaster"
        },
        {
            "title": "Pro Screwdriver Set (10pc)",
            "description": "Magnetic tips, chrome‑vanadium steel, organized storage tray.",
            "price": 24.5,
            "category": "hand-tools",
            "in_stock": True,
            "image_url": "https://images.unsplash.com/photo-1597692493640-5c0f1ca2ab40?q=80&w=1200&auto=format&fit=crop",
            "brand": "PrecisionX"
        },
        {
            "title": "Assorted Wood Screws (200pc)",
            "description": "Multi‑size zinc‑plated wood screws in resealable box.",
            "price": 12.49,
            "category": "fasteners",
            "in_stock": True,
            "image_url": "https://images.unsplash.com/photo-1610259110184-ef316b7cbb60?q=80&w=1200&auto=format&fit=crop",
            "brand": "GripTite"
        },
        {
            "title": "LED Work Light Rechargeable",
            "description": "1000‑lumen folding work light with magnetic base and USB‑C charging.",
            "price": 34.95,
            "category": "electrical",
            "in_stock": False,
            "image_url": "https://images.unsplash.com/photo-1487058792275-0ad4aaf24ca7?q=80&w=1200&auto=format&fit=crop",
            "brand": "BrightBeam"
        },
        {
            "title": "PTFE Thread Seal Tape (10 Rolls)",
            "description": "For leak‑free pipe fittings; 1/2 in. x 520 in.",
            "price": 9.99,
            "category": "plumbing",
            "in_stock": True,
            "image_url": "https://images.unsplash.com/photo-1503387762-592deb58ef4e?q=80&w=1200&auto=format&fit=crop",
            "brand": "SealSure"
        },
        {
            "title": "Interior Wall Paint, Satin 1 Gal",
            "description": "Low‑odor, quick‑drying acrylic latex paint; great coverage.",
            "price": 32.0,
            "category": "paint",
            "in_stock": True,
            "image_url": "https://images.unsplash.com/photo-1507666664345-c492233acf60?q=80&w=1200&auto=format&fit=crop",
            "brand": "ColorCraft"
        },
    ]

    inserted = 0
    for p in sample:
        # Avoid duplicates by title
        existing = db["product"].find_one({"title": p["title"]})
        if not existing:
            db["product"].insert_one(p)
            inserted += 1

    return {"inserted": inserted}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
