from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.common.database import get_db
from src.common.auth import get_current_user
from src.modules.assessment.services.assessment_service import AssessmentService
from src.modules.assessment.services.submission_service import SubmissionService

router = APIRouter(prefix="/assessments", tags=["Assessments"])

# Request/Response Models
class QuestionOption(BaseModel):
    """Question option model."""
    text: str
    is_correct: bool = False

class Question(BaseModel):
    """Assessment question model."""
    text: str
    type: str = Field(..., description="Type of question: 'multiple_choice', 'true_false', 'short_answer', 'essay'")
    options: Optional[List[QuestionOption]] = None
    points: int = Field(1, ge=1)
    explanation: Optional[str] = None

class AssessmentBase(BaseModel):
    """Base assessment model."""
    title: str
    description: str
    time_limit_minutes: Optional[int] = None
    passing_score: int = Field(70, ge=0, le=100)
    is_randomized: bool = False
    allow_multiple_attempts: bool = True
    max_attempts: Optional[int] = None
    course_id: UUID

class AssessmentCreateRequest(AssessmentBase):
    """Assessment creation request model."""
    questions: List[Question]

class AssessmentUpdateRequest(BaseModel):
    """Assessment update request model."""
    title: Optional[str] = None
    description: Optional[str] = None
    time_limit_minutes: Optional[int] = None
    passing_score: Optional[int] = Field(None, ge=0, le=100)
    is_randomized: Optional[bool] = None
    allow_multiple_attempts: Optional[bool] = None
    max_attempts: Optional[int] = None
    questions: Optional[List[Question]] = None

class QuestionResponse(BaseModel):
    """Question response model."""
    id: UUID
    text: str
    type: str
    options: Optional[List[Dict[str, Any]]] = None
    points: int
    explanation: Optional[str] = None

class AssessmentResponse(AssessmentBase):
    """Assessment response model."""
    id: UUID
    created_at: str
    updated_at: str
    questions: List[QuestionResponse]
    
    class Config:
        from_attributes = True

class SubmissionAnswerRequest(BaseModel):
    """Submission answer request model."""
    question_id: UUID
    selected_option_ids: Optional[List[UUID]] = None
    text_answer: Optional[str] = None

class AssessmentSubmissionRequest(BaseModel):
    """Assessment submission request model."""
    answers: List[SubmissionAnswerRequest]
    time_spent_seconds: int = Field(..., ge=0)

class SubmissionAnswerResponse(BaseModel):
    """Submission answer response model."""
    question_id: UUID
    is_correct: bool
    points_earned: int
    feedback: Optional[str] = None

class AssessmentSubmissionResponse(BaseModel):
    """Assessment submission response model."""
    id: UUID
    assessment_id: UUID
    score: int
    passed: bool
    completed_at: str
    time_spent_seconds: int
    answers: List[SubmissionAnswerResponse]

class AssessmentAttemptInfo(BaseModel):
    """Assessment attempt information model."""
    total_attempts: int
    remaining_attempts: Optional[int] = None
    latest_score: Optional[int] = None
    highest_score: Optional[int] = None
    passing_score: int
    latest_passed: bool = False

# Routes
@router.post("", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    assessment_data: AssessmentCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new assessment.
    
    Creates a new quiz or assessment with questions and answer options.
    """
    assessment_service = AssessmentService(db)
    
    try:
        assessment = await assessment_service.create_assessment(
            title=assessment_data.title,
            description=assessment_data.description,
            time_limit_minutes=assessment_data.time_limit_minutes,
            passing_score=assessment_data.passing_score,
            is_randomized=assessment_data.is_randomized,
            allow_multiple_attempts=assessment_data.allow_multiple_attempts,
            max_attempts=assessment_data.max_attempts,
            course_id=assessment_data.course_id,
            questions=assessment_data.questions,
            created_by=UUID(current_user["sub"])
        )
        
        questions_response = [
            QuestionResponse(
                id=question.id,
                text=question.text,
                type=question.type,
                options=[
                    {
                        "id": option.id,
                        "text": option.text
                    } for option in question.options
                ] if question.options else None,
                points=question.points,
                explanation=question.explanation
            ) for question in assessment.questions
        ]
        
        return AssessmentResponse(
            id=assessment.id,
            title=assessment.title,
            description=assessment.description,
            time_limit_minutes=assessment.time_limit_minutes,
            passing_score=assessment.passing_score,
            is_randomized=assessment.is_randomized,
            allow_multiple_attempts=assessment.allow_multiple_attempts,
            max_attempts=assessment.max_attempts,
            course_id=assessment.course_id,
            created_at=assessment.created_at.isoformat(),
            updated_at=assessment.updated_at.isoformat(),
            questions=questions_response
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("", response_model=List[AssessmentResponse])
async def list_assessments(
    course_id: Optional[UUID] = Query(None, description="Filter by course ID"),
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List assessments.
    
    Returns a list of assessments, optionally filtered by course.
    """
    assessment_service = AssessmentService(db)
    assessments = await assessment_service.list_assessments(
        course_id=course_id,
        limit=limit,
        offset=offset
    )
    
    result = []
    for assessment in assessments:
        questions_response = [
            QuestionResponse(
                id=question.id,
                text=question.text,
                type=question.type,
                options=[
                    {
                        "id": option.id,
                        "text": option.text
                    } for option in question.options
                ] if question.options else None,
                points=question.points,
                explanation=question.explanation
            ) for question in assessment.questions
        ]
        
        result.append(AssessmentResponse(
            id=assessment.id,
            title=assessment.title,
            description=assessment.description,
            time_limit_minutes=assessment.time_limit_minutes,
            passing_score=assessment.passing_score,
            is_randomized=assessment.is_randomized,
            allow_multiple_attempts=assessment.allow_multiple_attempts,
            max_attempts=assessment.max_attempts,
            course_id=assessment.course_id,
            created_at=assessment.created_at.isoformat(),
            updated_at=assessment.updated_at.isoformat(),
            questions=questions_response
        ))
    
    return result

@router.get("/{assessment_id}", response_model=AssessmentResponse)
async def get_assessment(
    assessment_id: UUID = Path(..., description="The ID of the assessment to retrieve"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific assessment by ID.
    
    Returns the assessment data with its questions.
    """
    assessment_service = AssessmentService(db)
    assessment = await assessment_service.get_assessment(assessment_id)
    
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )
    
    questions_response = [
        QuestionResponse(
            id=question.id,
            text=question.text,
            type=question.type,
            options=[
                {
                    "id": option.id,
                    "text": option.text
                } for option in question.options
            ] if question.options else None,
            points=question.points,
            explanation=question.explanation
        ) for question in assessment.questions
    ]
    
    return AssessmentResponse(
        id=assessment.id,
        title=assessment.title,
        description=assessment.description,
        time_limit_minutes=assessment.time_limit_minutes,
        passing_score=assessment.passing_score,
        is_randomized=assessment.is_randomized,
        allow_multiple_attempts=assessment.allow_multiple_attempts,
        max_attempts=assessment.max_attempts,
        course_id=assessment.course_id,
        created_at=assessment.created_at.isoformat(),
        updated_at=assessment.updated_at.isoformat(),
        questions=questions_response
    )

@router.put("/{assessment_id}", response_model=AssessmentResponse)
async def update_assessment(
    assessment_data: AssessmentUpdateRequest,
    assessment_id: UUID = Path(..., description="The ID of the assessment to update"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an assessment.
    
    Updates an existing assessment with new data.
    """
    assessment_service = AssessmentService(db)
    
    try:
        assessment = await assessment_service.update_assessment(
            assessment_id=assessment_id,
            title=assessment_data.title,
            description=assessment_data.description,
            time_limit_minutes=assessment_data.time_limit_minutes,
            passing_score=assessment_data.passing_score,
            is_randomized=assessment_data.is_randomized,
            allow_multiple_attempts=assessment_data.allow_multiple_attempts,
            max_attempts=assessment_data.max_attempts,
            questions=assessment_data.questions,
            updated_by=UUID(current_user["sub"])
        )
        
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not found"
            )
        
        questions_response = [
            QuestionResponse(
                id=question.id,
                text=question.text,
                type=question.type,
                options=[
                    {
                        "id": option.id,
                        "text": option.text
                    } for option in question.options
                ] if question.options else None,
                points=question.points,
                explanation=question.explanation
            ) for question in assessment.questions
        ]
        
        return AssessmentResponse(
            id=assessment.id,
            title=assessment.title,
            description=assessment.description,
            time_limit_minutes=assessment.time_limit_minutes,
            passing_score=assessment.passing_score,
            is_randomized=assessment.is_randomized,
            allow_multiple_attempts=assessment.allow_multiple_attempts,
            max_attempts=assessment.max_attempts,
            course_id=assessment.course_id,
            created_at=assessment.created_at.isoformat(),
            updated_at=assessment.updated_at.isoformat(),
            questions=questions_response
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assessment(
    assessment_id: UUID = Path(..., description="The ID of the assessment to delete"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an assessment.
    
    Removes an assessment and its associated questions.
    """
    assessment_service = AssessmentService(db)
    success = await assessment_service.delete_assessment(
        assessment_id=assessment_id,
        deleted_by=UUID(current_user["sub"])
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )
    
    return None

@router.post("/{assessment_id}/submit", response_model=AssessmentSubmissionResponse)
async def submit_assessment(
    submission_data: AssessmentSubmissionRequest,
    assessment_id: UUID = Path(..., description="The ID of the assessment to submit"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit assessment answers.
    
    Submits a user's answers for an assessment and returns the results.
    """
    submission_service = SubmissionService(db)
    
    try:
        submission = await submission_service.submit_assessment(
            assessment_id=assessment_id,
            user_id=UUID(current_user["sub"]),
            answers=submission_data.answers,
            time_spent_seconds=submission_data.time_spent_seconds
        )
        
        answers_response = [
            SubmissionAnswerResponse(
                question_id=answer.question_id,
                is_correct=answer.is_correct,
                points_earned=answer.points_earned,
                feedback=answer.feedback
            ) for answer in submission.answers
        ]
        
        return AssessmentSubmissionResponse(
            id=submission.id,
            assessment_id=submission.assessment_id,
            score=submission.score,
            passed=submission.passed,
            completed_at=submission.completed_at.isoformat(),
            time_spent_seconds=submission.time_spent_seconds,
            answers=answers_response
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{assessment_id}/attempts", response_model=AssessmentAttemptInfo)
async def get_assessment_attempts(
    assessment_id: UUID = Path(..., description="The ID of the assessment to check attempts for"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get assessment attempt information.
    
    Returns information about a user's attempts at an assessment.
    """
    submission_service = SubmissionService(db)
    assessment_service = AssessmentService(db)
    
    assessment = await assessment_service.get_assessment(assessment_id)
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )
    
    attempt_info = await submission_service.get_attempt_info(
        assessment_id=assessment_id,
        user_id=UUID(current_user["sub"])
    )
    
    return AssessmentAttemptInfo(
        total_attempts=attempt_info["total_attempts"],
        remaining_attempts=attempt_info.get("remaining_attempts"),
        latest_score=attempt_info.get("latest_score"),
        highest_score=attempt_info.get("highest_score"),
        passing_score=assessment.passing_score,
        latest_passed=attempt_info.get("latest_passed", False)
    )
