from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from api.auth import verify_token
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import database as db

router = APIRouter(prefix="/api/faq", tags=["faq"])


class FaqRequest(BaseModel):
    question: str
    answer: str
    keywords: str = ""
    lang: str = ""


@router.get("")
def list_faqs(_: str = Depends(verify_token)):
    return {"faqs": [dict(r) for r in db.get_faqs()]}


@router.post("")
def create_faq(body: FaqRequest, _: str = Depends(verify_token)):
    if not body.question.strip() or not body.answer.strip():
        raise HTTPException(status_code=400, detail="question and answer are required")
    fid = db.add_faq(body.question.strip(), body.answer.strip(),
                     body.keywords.strip(), body.lang.strip())
    return {"success": True, "id": fid}


@router.put("/{fid}")
def edit_faq(fid: int, body: FaqRequest, _: str = Depends(verify_token)):
    if not body.question.strip() or not body.answer.strip():
        raise HTTPException(status_code=400, detail="question and answer are required")
    db.update_faq(fid, body.question.strip(), body.answer.strip(),
                  body.keywords.strip(), body.lang.strip())
    return {"success": True}


@router.delete("/{fid}")
def remove_faq(fid: int, _: str = Depends(verify_token)):
    db.delete_faq(fid)
    return {"success": True}
