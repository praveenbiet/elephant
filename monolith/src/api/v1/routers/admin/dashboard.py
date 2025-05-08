from typing import List, Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.common.database import get_db
from src.common.auth import get_current_admin_user
from src.modules.admin.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Admin Dashboard"])

# Request/Response Models
class CountSummary(BaseModel):
    """Count summary model."""
    users: int
    courses: int
    videos: int
    assessments: int
    learning_paths: int
    subscriptions: Dict[str, int]

class RevenueData(BaseModel):
    """Revenue data model."""
    total: float
    monthly_recurring: float
    yearly_recurring: float
    period_comparison: Dict[str, Any]
    
class UserRegistrationData(BaseModel):
    """User registration data model."""
    total: int
    period: Dict[str, Any]
    comparison: Dict[str, Any]

class TimeSeriesPoint(BaseModel):
    """Time series data point model."""
    date: str
    value: float

class TimeSeriesData(BaseModel):
    """Time series data model."""
    data: List[TimeSeriesPoint]
    
class TopItem(BaseModel):
    """Top item model."""
    id: str
    title: str
    value: float
    
class TopItemsData(BaseModel):
    """Top items data model."""
    courses: List[TopItem]
    instructors: List[TopItem]
    learning_paths: List[TopItem]

class DashboardSummary(BaseModel):
    """Dashboard summary model."""
    counts: CountSummary
    revenue: RevenueData
    registrations: UserRegistrationData
    top_items: TopItemsData

# Routes
@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    period: str = Query("30d", description="Period for comparison: '7d', '30d', '90d', '1y'"),
    current_user: Dict[str, Any] = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get dashboard summary.
    
    Returns a summary of key metrics for the admin dashboard.
    """
    dashboard_service = DashboardService(db)
    
    # Validate period
    valid_periods = ["7d", "30d", "90d", "1y"]
    if period not in valid_periods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}"
        )
    
    summary = await dashboard_service.get_dashboard_summary(period=period)
    
    return DashboardSummary(
        counts=CountSummary(
            users=summary["counts"]["users"],
            courses=summary["counts"]["courses"],
            videos=summary["counts"]["videos"],
            assessments=summary["counts"]["assessments"],
            learning_paths=summary["counts"]["learning_paths"],
            subscriptions=summary["counts"]["subscriptions"]
        ),
        revenue=RevenueData(
            total=summary["revenue"]["total"],
            monthly_recurring=summary["revenue"]["monthly_recurring"],
            yearly_recurring=summary["revenue"]["yearly_recurring"],
            period_comparison=summary["revenue"]["period_comparison"]
        ),
        registrations=UserRegistrationData(
            total=summary["registrations"]["total"],
            period=summary["registrations"]["period"],
            comparison=summary["registrations"]["comparison"]
        ),
        top_items=TopItemsData(
            courses=[
                TopItem(
                    id=course["id"],
                    title=course["title"],
                    value=course["value"]
                ) for course in summary["top_items"]["courses"]
            ],
            instructors=[
                TopItem(
                    id=instructor["id"],
                    title=instructor["title"],
                    value=instructor["value"]
                ) for instructor in summary["top_items"]["instructors"]
            ],
            learning_paths=[
                TopItem(
                    id=path["id"],
                    title=path["title"],
                    value=path["value"]
                ) for path in summary["top_items"]["learning_paths"]
            ]
        )
    )

@router.get("/revenue/timeseries", response_model=TimeSeriesData)
async def get_revenue_timeseries(
    period: str = Query("30d", description="Period: '7d', '30d', '90d', '1y'"),
    interval: str = Query("day", description="Interval: 'day', 'week', 'month'"),
    current_user: Dict[str, Any] = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get revenue time series data.
    
    Returns time series data for revenue over the specified period and interval.
    """
    dashboard_service = DashboardService(db)
    
    # Validate period
    valid_periods = ["7d", "30d", "90d", "1y"]
    if period not in valid_periods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}"
        )
    
    # Validate interval
    valid_intervals = ["day", "week", "month"]
    if interval not in valid_intervals:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid interval. Must be one of: {', '.join(valid_intervals)}"
        )
    
    time_series = await dashboard_service.get_revenue_timeseries(
        period=period,
        interval=interval
    )
    
    return TimeSeriesData(
        data=[
            TimeSeriesPoint(
                date=point["date"].isoformat(),
                value=point["value"]
            ) for point in time_series
        ]
    )

@router.get("/registrations/timeseries", response_model=TimeSeriesData)
async def get_registrations_timeseries(
    period: str = Query("30d", description="Period: '7d', '30d', '90d', '1y'"),
    interval: str = Query("day", description="Interval: 'day', 'week', 'month'"),
    current_user: Dict[str, Any] = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user registrations time series data.
    
    Returns time series data for user registrations over the specified period and interval.
    """
    dashboard_service = DashboardService(db)
    
    # Validate period
    valid_periods = ["7d", "30d", "90d", "1y"]
    if period not in valid_periods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}"
        )
    
    # Validate interval
    valid_intervals = ["day", "week", "month"]
    if interval not in valid_intervals:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid interval. Must be one of: {', '.join(valid_intervals)}"
        )
    
    time_series = await dashboard_service.get_registrations_timeseries(
        period=period,
        interval=interval
    )
    
    return TimeSeriesData(
        data=[
            TimeSeriesPoint(
                date=point["date"].isoformat(),
                value=point["value"]
            ) for point in time_series
        ]
    )

@router.get("/subscriptions/timeseries", response_model=TimeSeriesData)
async def get_subscriptions_timeseries(
    period: str = Query("30d", description="Period: '7d', '30d', '90d', '1y'"),
    interval: str = Query("day", description="Interval: 'day', 'week', 'month'"),
    plan_id: str = Query(None, description="Filter by subscription plan ID"),
    current_user: Dict[str, Any] = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get subscriptions time series data.
    
    Returns time series data for subscriptions over the specified period and interval.
    """
    dashboard_service = DashboardService(db)
    
    # Validate period
    valid_periods = ["7d", "30d", "90d", "1y"]
    if period not in valid_periods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}"
        )
    
    # Validate interval
    valid_intervals = ["day", "week", "month"]
    if interval not in valid_intervals:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid interval. Must be one of: {', '.join(valid_intervals)}"
        )
    
    time_series = await dashboard_service.get_subscriptions_timeseries(
        period=period,
        interval=interval,
        plan_id=plan_id
    )
    
    return TimeSeriesData(
        data=[
            TimeSeriesPoint(
                date=point["date"].isoformat(),
                value=point["value"]
            ) for point in time_series
        ]
    )
