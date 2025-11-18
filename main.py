import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product

app = FastAPI(title="Hardware Store API", version="1.0.0")

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


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
