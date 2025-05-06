from typing import List, Optional, Dict, Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.logger import get_logger
from src.modules.courses.domain.category import Category, Subcategory
from src.modules.courses.persistence.category_repository import CategoryRepository

logger = get_logger(__name__)

class CategoryService:
    """
    Service for course category-related operations.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.category_repository = CategoryRepository(db)
    
    async def get_category_by_id(self, category_id: str) -> Optional[Category]:
        """Get a category by ID."""
        return await self.category_repository.get_category_by_id(category_id)
    
    async def get_category_by_slug(self, slug: str) -> Optional[Category]:
        """Get a category by slug."""
        return await self.category_repository.get_category_by_slug(slug)
    
    async def list_categories(
        self,
        active_only: bool = True,
        sort_by: str = "position",
        sort_order: str = "asc"
    ) -> List[Category]:
        """
        List all categories with optional filtering and sorting.
        
        Args:
            active_only: Whether to include only active categories
            sort_by: Field to sort by
            sort_order: Sort order ("asc" or "desc")
            
        Returns:
            List of category domain entities
        """
        try:
            return await self.category_repository.list_categories(
                active_only=active_only,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
        except Exception as e:
            logger.error(f"Error listing categories: {str(e)}", exc_info=True)
            return []
    
    async def create_category(self, category_data: Dict[str, Any]) -> Optional[Category]:
        """
        Create a new category.
        
        Args:
            category_data: Dictionary with category data
            
        Returns:
            Created category domain entity or None if creation failed
        """
        try:
            # Generate ID if not provided
            category_id = category_data.get('id') or str(uuid.uuid4())
            
            # Create category domain entity
            category = Category(
                id=category_id,
                name=category_data['name'],
                slug=category_data.get('slug'),
                description=category_data.get('description'),
                icon_url=category_data.get('icon_url'),
                image_url=category_data.get('image_url'),
                position=category_data.get('position', 0),
                is_active=category_data.get('is_active', True)
            )
            
            return await self.category_repository.create_category(category)
            
        except Exception as e:
            logger.error(f"Error creating category: {str(e)}", exc_info=True)
            return None
    
    async def update_category(self, category_id: str, category_data: Dict[str, Any]) -> Optional[Category]:
        """
        Update an existing category.
        
        Args:
            category_id: ID of the category to update
            category_data: Dictionary with updated category data
            
        Returns:
            Updated category domain entity or None if update failed
        """
        try:
            # Get existing category
            category = await self.category_repository.get_category_by_id(category_id)
            if not category:
                logger.error(f"Category with ID {category_id} not found for update")
                return None
            
            # Update category attributes
            if 'name' in category_data:
                category.name = category_data['name']
            if 'description' in category_data:
                category.description = category_data['description']
            if 'icon_url' in category_data:
                category.icon_url = category_data['icon_url']
            if 'image_url' in category_data:
                category.image_url = category_data['image_url']
            if 'position' in category_data:
                category.position = category_data['position']
            if 'is_active' in category_data:
                category.is_active = category_data['is_active']
            
            return await self.category_repository.update_category(category)
            
        except Exception as e:
            logger.error(f"Error updating category {category_id}: {str(e)}", exc_info=True)
            return None
    
    async def delete_category(self, category_id: str) -> bool:
        """
        Delete a category.
        
        Args:
            category_id: ID of the category to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return await self.category_repository.delete_category(category_id)
            
        except Exception as e:
            logger.error(f"Error deleting category {category_id}: {str(e)}", exc_info=True)
            return False
    
    async def get_subcategory_by_id(self, subcategory_id: str) -> Optional[Subcategory]:
        """Get a subcategory by ID."""
        return await self.category_repository.get_subcategory_by_id(subcategory_id)
    
    async def get_subcategory_by_slug(self, slug: str) -> Optional[Subcategory]:
        """Get a subcategory by slug."""
        return await self.category_repository.get_subcategory_by_slug(slug)
    
    async def list_subcategories(
        self,
        category_id: Optional[str] = None,
        active_only: bool = True,
        sort_by: str = "position",
        sort_order: str = "asc"
    ) -> List[Subcategory]:
        """
        List subcategories with optional filtering and sorting.
        
        Args:
            category_id: Optional parent category ID to filter by
            active_only: Whether to include only active subcategories
            sort_by: Field to sort by
            sort_order: Sort order ("asc" or "desc")
            
        Returns:
            List of subcategory domain entities
        """
        try:
            return await self.category_repository.list_subcategories(
                category_id=category_id,
                active_only=active_only,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
        except Exception as e:
            logger.error(f"Error listing subcategories: {str(e)}", exc_info=True)
            return []
    
    async def create_subcategory(self, subcategory_data: Dict[str, Any]) -> Optional[Subcategory]:
        """
        Create a new subcategory.
        
        Args:
            subcategory_data: Dictionary with subcategory data
            
        Returns:
            Created subcategory domain entity or None if creation failed
        """
        try:
            # Verify parent category exists
            parent_category = await self.category_repository.get_category_by_id(subcategory_data['category_id'])
            if not parent_category:
                logger.error(f"Parent category {subcategory_data['category_id']} not found for subcategory creation")
                return None
            
            # Generate ID if not provided
            subcategory_id = subcategory_data.get('id') or str(uuid.uuid4())
            
            # Create subcategory domain entity
            subcategory = Subcategory(
                id=subcategory_id,
                category_id=subcategory_data['category_id'],
                name=subcategory_data['name'],
                slug=subcategory_data.get('slug'),
                description=subcategory_data.get('description'),
                image_url=subcategory_data.get('image_url'),
                position=subcategory_data.get('position', 0),
                is_active=subcategory_data.get('is_active', True)
            )
            
            return await self.category_repository.create_subcategory(subcategory)
            
        except Exception as e:
            logger.error(f"Error creating subcategory: {str(e)}", exc_info=True)
            return None
    
    async def update_subcategory(self, subcategory_id: str, subcategory_data: Dict[str, Any]) -> Optional[Subcategory]:
        """
        Update an existing subcategory.
        
        Args:
            subcategory_id: ID of the subcategory to update
            subcategory_data: Dictionary with updated subcategory data
            
        Returns:
            Updated subcategory domain entity or None if update failed
        """
        try:
            # Get existing subcategory
            subcategory = await self.category_repository.get_subcategory_by_id(subcategory_id)
            if not subcategory:
                logger.error(f"Subcategory with ID {subcategory_id} not found for update")
                return None
            
            # Update subcategory attributes
            if 'name' in subcategory_data:
                subcategory.name = subcategory_data['name']
            if 'description' in subcategory_data:
                subcategory.description = subcategory_data['description']
            if 'image_url' in subcategory_data:
                subcategory.image_url = subcategory_data['image_url']
            if 'position' in subcategory_data:
                subcategory.position = subcategory_data['position']
            if 'is_active' in subcategory_data:
                subcategory.is_active = subcategory_data['is_active']
            
            return await self.category_repository.update_subcategory(subcategory)
            
        except Exception as e:
            logger.error(f"Error updating subcategory {subcategory_id}: {str(e)}", exc_info=True)
            return None
    
    async def delete_subcategory(self, subcategory_id: str) -> bool:
        """
        Delete a subcategory.
        
        Args:
            subcategory_id: ID of the subcategory to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return await self.category_repository.delete_subcategory(subcategory_id)
            
        except Exception as e:
            logger.error(f"Error deleting subcategory {subcategory_id}: {str(e)}", exc_info=True)
            return False
    
    async def get_category_with_subcategories(self, category_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a category with all its subcategories.
        
        Args:
            category_id: Category ID
            
        Returns:
            Dictionary with category and subcategories
        """
        try:
            return await self.category_repository.get_category_with_subcategories(category_id)
            
        except Exception as e:
            logger.error(f"Error getting category with subcategories for {category_id}: {str(e)}", exc_info=True)
            return None
    
    async def get_all_categories_with_subcategories(
        self,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all categories with their subcategories.
        
        Args:
            active_only: Whether to include only active categories and subcategories
            
        Returns:
            List of dictionaries with categories and their subcategories
        """
        try:
            return await self.category_repository.get_all_categories_with_subcategories(
                active_only=active_only
            )
            
        except Exception as e:
            logger.error(f"Error getting all categories with subcategories: {str(e)}", exc_info=True)
            return [] 