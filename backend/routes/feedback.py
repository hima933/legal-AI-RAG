from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from bson import ObjectId

from database.mongo import db, queries_collection
from routes.auth import get_current_user

router = APIRouter()
feedback_collection = db["query_feedback"]


class FeedbackRequest(BaseModel):
    query_id: str = Field(..., min_length=8)
    rating: Literal["up", "down"]
    correction: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    details: Optional[str] = None


@router.post("/feedback")
async def submit_feedback(payload: FeedbackRequest, current_user=Depends(get_current_user)):
    try:
        clean_feedback = {
            "query_id": payload.query_id.strip(),
            "user_id": str(current_user["_id"]),
            "rating": payload.rating,
            "correction": (payload.correction or "").strip()[:2000],
            "details": (payload.details or "").strip()[:2000],
            "tags": [str(tag).strip() for tag in payload.tags if str(tag).strip()][:10],
            "updated_at": datetime.utcnow(),
        }

        feedback_collection.update_one(
            {"query_id": clean_feedback["query_id"], "user_id": clean_feedback["user_id"]},
            {"$set": clean_feedback, "$setOnInsert": {"created_at": datetime.utcnow()}},
            upsert=True,
        )

        query_filter = {"_id": payload.query_id}
        if ObjectId.is_valid(payload.query_id):
            query_filter = {"_id": ObjectId(payload.query_id)}

        queries_collection.update_one(
            query_filter,
            {
                "$set": {
                    "feedback.rating": payload.rating,
                    "feedback.correction": clean_feedback["correction"],
                    "feedback.updated_at": clean_feedback["updated_at"],
                }
            },
        )

        return {"status": "success", "message": "Feedback saved"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save feedback: {exc}") from exc


@router.get("/feedback")
async def list_my_feedback(current_user=Depends(get_current_user)):
    try:
        items = list(
            feedback_collection.find({"user_id": str(current_user["_id"])})
            .sort("updated_at", -1)
            .limit(100)
        )
        for item in items:
            item["_id"] = str(item["_id"])
        return {"status": "success", "feedback": items}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch feedback: {exc}") from exc
