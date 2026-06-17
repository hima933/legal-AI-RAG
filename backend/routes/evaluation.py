from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from database.mongo import db
from routes.auth import get_current_user

router = APIRouter()
evaluation_collection = db["query_evaluations"]
feedback_collection = db["query_feedback"]


@router.get("/eval/summary")
async def evaluation_summary(
    days: int = Query(default=30, ge=1, le=365),
    release_version: Optional[str] = Query(default=None),
    current_user=Depends(get_current_user),
):
    try:
        since = datetime.utcnow() - timedelta(days=days)
        match = {
            "timestamp": {"$gte": since},
            "user_id": str(current_user["_id"]),
        }
        if release_version:
            match["release_version"] = release_version

        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": "$release_version",
                    "total_queries": {"$sum": 1},
                    "avg_faithfulness": {"$avg": "$metrics.faithfulness_score"},
                    "avg_hallucination_risk": {"$avg": "$metrics.hallucination_risk"},
                    "avg_precision_at_k": {"$avg": "$metrics.precision_at_k"},
                    "avg_recall_at_k": {"$avg": "$metrics.recall_at_k"},
                    "avg_citation_coverage": {"$avg": "$metrics.citation_coverage"},
                    "second_pass_count": {
                        "$sum": {"$cond": [{"$eq": ["$second_pass_used", True]}, 1, 0]}
                    },
                }
            },
            {"$sort": {"total_queries": -1}},
        ]

        grouped = list(evaluation_collection.aggregate(pipeline))

        feedback_match = {"updated_at": {"$gte": since}, "user_id": str(current_user["_id"])}
        feedback_summary = list(
            feedback_collection.aggregate(
                [
                    {"$match": feedback_match},
                    {"$group": {"_id": "$rating", "count": {"$sum": 1}}},
                ]
            )
        )
        feedback_counts = {item["_id"]: item["count"] for item in feedback_summary}

        releases = []
        for row in grouped:
            total = row.get("total_queries", 0) or 0
            second_pass_ratio = (row.get("second_pass_count", 0) / total) if total else 0.0
            releases.append(
                {
                    "release_version": row.get("_id") or "unknown",
                    "total_queries": total,
                    "avg_faithfulness": round(float(row.get("avg_faithfulness") or 0.0), 3),
                    "avg_hallucination_risk": round(float(row.get("avg_hallucination_risk") or 0.0), 3),
                    "avg_precision_at_k": round(float(row.get("avg_precision_at_k") or 0.0), 3),
                    "avg_recall_at_k": round(float(row.get("avg_recall_at_k") or 0.0), 3),
                    "avg_citation_coverage": round(float(row.get("avg_citation_coverage") or 0.0), 3),
                    "second_pass_ratio": round(second_pass_ratio, 3),
                }
            )

        return {
            "status": "success",
            "window_days": days,
            "releases": releases,
            "feedback": {
                "up": int(feedback_counts.get("up", 0)),
                "down": int(feedback_counts.get("down", 0)),
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to build evaluation summary: {exc}") from exc
