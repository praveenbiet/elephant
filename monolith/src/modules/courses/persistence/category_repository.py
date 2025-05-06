import uuid
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any

from sqlalchemy import select, update, delete, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from src.common.logger import get_logger
from src.modules.courses.domain.category import Category, Subcategory
from src.modules.courses.models.category import CategoryModel, SubcategoryModel

logger = get_logger(__name__)

class CategoryRepository:
    """
    Repository for category-related database operations.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_category_by_id(self, category_id: str) -> Optional[Category]:
        """
        Get a category by ID.
        
        Args:
            category_id: Category ID
            
        Returns:
            Category domain entity if found, None otherwise
        """
        try:
            query = select(CategoryModel).where(CategoryModel.id == category_id)
            result = await self.db.execute(query)
            category_model = result.scalars().first()
            
            if not category_model:
                return None
                
            return self._map_category_to_domain(category_model)
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting category by ID {category_id}: {str(e)}", exc_info=True)
            return None
    
    async def get_category_by_slug(self, slug: str) -> Optional[Category]:
        """
        Get a category by slug.
        
        Args:
            slug: Category slug
            
        Returns:
            Category domain entity if found, None otherwise
        """
        try:
            query = select(CategoryModel).where(CategoryModel.slug == slug)
            result = await self.db.execute(query)
            category_model = result.scalars().first()
            
            if not category_model:
                return None
                
            return self._map_category_to_domain(category_model)
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting category by slug {slug}: {str(e)}", exc_info=True)
            return None
    
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
            # Build query
            query = select(CategoryModel)
            
            # Apply filters
            if active_only:
                query = query.where(CategoryModel.is_active == True)
            
            # Apply sorting
            sort_column = getattr(CategoryModel, sort_by, CategoryModel.position)
            if sort_order.lower() == "asc":
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(desc(sort_column))
            
            # Execute query
            result = await self.db.execute(query)
            category_models = result.scalars().all()
            
            # Map to domain entities
            categories = [self._map_category_to_domain(model) for model in category_models]
            
            return categories
            
        except SQLAlchemyError as e:
            logger.error(f"Error listing categories: {str(e)}", exc_info=True)
            return []
    
    async def create_category(self, category: Category) -> Optional[Category]:
        """
        Create a new category.
        
        Args:
            category: Category domain entity
            
        Returns:
            Created category domain entity with ID, or None if creation failed
        """
        try:
            # Generate ID if not provided
            if not category.id:
                category.id = str(uuid.uuid4())
            
            # Generate slug if not provided
            if not category.slug:
                base_slug = self._generate_slug_from_name(category.name)
                category.slug = await self._ensure_unique_category_slug(base_slug)
            
            # Create model from domain entity
            category_model = CategoryModel(
                id=category.id,
                name=category.name,
                slug=category.slug,
                description=category.description,
                icon_url=category.icon_url,
                image_url=category.image_url,
                position=category.position,
                is_active=category.is_active,
                created_at=category.created_at or datetime.utcnow(),
                updated_at=category.updated_at or datetime.utcnow()
            )
            
            self.db.add(category_model)
            await self.db.commit()
            await self.db.refresh(category_model)
            
            # Return domain entity with updated data
            return self._map_category_to_domain(category_model)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error creating category {category.name}: {str(e)}", exc_info=True)
            return None
    
    async def update_category(self, category: Category) -> Optional[Category]:
        """
        Update an existing category.
        
        Args:
            category: Category domain entity with updated values
            
        Returns:
            Updated category domain entity, or None if update failed
        """
        try:
            # Check if category exists
            existing_category = await self.get_category_by_id(category.id)
            if not existing_category:
                logger.error(f"Category with ID {category.id} not found for update")
                return None
            
            # Update the category
            query = update(CategoryModel).where(CategoryModel.id == category.id).values(
                name=category.name,
                description=category.description,
                icon_url=category.icon_url,
                image_url=category.image_url,
                position=category.position,
                is_active=category.is_active,
                updated_at=datetime.utcnow()
            )
            
            await self.db.execute(query)
            await self.db.commit()
            
            # Get the updated category
            return await self.get_category_by_id(category.id)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error updating category {category.id}: {str(e)}", exc_info=True)
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
            query = delete(CategoryModel).where(CategoryModel.id == category_id)
            result = await self.db.execute(query)
            await self.db.commit()
            
            return result.rowcount > 0
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error deleting category {category_id}: {str(e)}", exc_info=True)
            return False
    
    async def get_subcategory_by_id(self, subcategory_id: str) -> Optional[Subcategory]:
        """
        Get a subcategory by ID.
        
        Args:
            subcategory_id: Subcategory ID
            
        Returns:
            Subcategory domain entity if found, None otherwise
        """
        try:
            query = select(SubcategoryModel).where(SubcategoryModel.id == subcategory_id)
            result = await self.db.execute(query)
            subcategory_model = result.scalars().first()
            
            if not subcategory_model:
                return None
                
            return self._map_subcategory_to_domain(subcategory_model)
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting subcategory by ID {subcategory_id}: {str(e)}", exc_info=True)
            return None
    
    async def get_subcategory_by_slug(self, slug: str) -> Optional[Subcategory]:
        """
        Get a subcategory by slug.
        
        Args:
            slug: Subcategory slug
            
        Returns:
            Subcategory domain entity if found, None otherwise
        """
        try:
            query = select(SubcategoryModel).where(SubcategoryModel.slug == slug)
            result = await self.db.execute(query)
            subcategory_model = result.scalars().first()
            
            if not subcategory_model:
                return None
                
            return self._map_subcategory_to_domain(subcategory_model)
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting subcategory by slug {slug}: {str(e)}", exc_info=True)
            return None
    
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
            # Build query
            query = select(SubcategoryModel)
            
            # Apply filters
            if category_id:
                query = query.where(SubcategoryModel.category_id == category_id)
                
            if active_only:
                query = query.where(SubcategoryModel.is_active == True)
            
            # Apply sorting
            sort_column = getattr(SubcategoryModel, sort_by, SubcategoryModel.position)
            if sort_order.lower() == "asc":
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(desc(sort_column))
            
            # Execute query
            result = await self.db.execute(query)
            subcategory_models = result.scalars().all()
            
            # Map to domain entities
            subcategories = [self._map_subcategory_to_domain(model) for model in subcategory_models]
            
            return subcategories
            
        except SQLAlchemyError as e:
            logger.error(f"Error listing subcategories: {str(e)}", exc_info=True)
            return []
    
    async def create_subcategory(self, subcategory: Subcategory) -> Optional[Subcategory]:
        """
        Create a new subcategory.
        
        Args:
            subcategory: Subcategory domain entity
            
        Returns:
            Created subcategory domain entity with ID, or None if creation failed
        """
        try:
            # Verify parent category exists
            parent_category = await self.get_category_by_id(subcategory.category_id)
            if not parent_category:
                logger.error(f"Parent category {subcategory.category_id} not found")
                return None
            
            # Generate ID if not provided
            if not subcategory.id:
                subcategory.id = str(uuid.uuid4())
            
            # Generate slug if not provided
            if not subcategory.slug:
                base_slug = self._generate_slug_from_name(subcategory.name)
                subcategory.slug = await self._ensure_unique_subcategory_slug(base_slug)
            
            # Create model from domain entity
            subcategory_model = SubcategoryModel(
                id=subcategory.id,
                category_id=subcategory.category_id,
                name=subcategory.name,
                slug=subcategory.slug,
                description=subcategory.description,
                image_url=subcategory.image_url,
                position=subcategory.position,
                is_active=subcategory.is_active,
                created_at=subcategory.created_at or datetime.utcnow(),
                updated_at=subcategory.updated_at or datetime.utcnow()
            )
            
            self.db.add(subcategory_model)
            await self.db.commit()
            await self.db.refresh(subcategory_model)
            
            # Return domain entity with updated data
            return self._map_subcategory_to_domain(subcategory_model)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error creating subcategory {subcategory.name}: {str(e)}", exc_info=True)
            return None
    
    async def update_subcategory(self, subcategory: Subcategory) -> Optional[Subcategory]:
        """
        Update an existing subcategory.
        
        Args:
            subcategory: Subcategory domain entity with updated values
            
        Returns:
            Updated subcategory domain entity, or None if update failed
        """
        try:
            # Check if subcategory exists
            existing_subcategory = await self.get_subcategory_by_id(subcategory.id)
            if not existing_subcategory:
                logger.error(f"Subcategory with ID {subcategory.id} not found for update")
                return None
            
            # Update the subcategory
            query = update(SubcategoryModel).where(SubcategoryModel.id == subcategory.id).values(
                name=subcategory.name,
                description=subcategory.description,
                image_url=subcategory.image_url,
                position=subcategory.position,
                is_active=subcategory.is_active,
                updated_at=datetime.utcnow()
            )
            
            await self.db.execute(query)
            await self.db.commit()
            
            # Get the updated subcategory
            return await self.get_subcategory_by_id(subcategory.id)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error updating subcategory {subcategory.id}: {str(e)}", exc_info=True)
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
            query = delete(SubcategoryModel).where(SubcategoryModel.id == subcategory_id)
            result = await self.db.execute(query)
            await self.db.commit()
            
            return result.rowcount > 0
            
        except SQLAlchemyError as e:
            await self.db.rollback()
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
            # Get category
            category = await self.get_category_by_id(category_id)
            if not category:
                return None
            
            # Get subcategories
            subcategories = await self.list_subcategories(category_id=category_id)
            
            return {
                "category": category,
                "subcategories": subcategories
            }
            
        except SQLAlchemyError as e:
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
            # Get all categories
            categories = await self.list_categories(active_only=active_only)
            
            # For each category, get its subcategories
            result = []
            for category in categories:
                subcategories = await self.list_subcategories(
                    category_id=category.id,
                    active_only=active_only
                )
                
                result.append({
                    "category": category,
                    "subcategories": subcategories
                })
            
            return result
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting all categories with subcategories: {str(e)}", exc_info=True)
            return []
    
    async def _ensure_unique_category_slug(self, base_slug: str) -> str:
        """
        Ensure a category slug is unique by appending a number if necessary.
        
        Args:
            base_slug: Base slug to check
            
        Returns:
            Unique slug
        """
        slug = base_slug
        counter = 1
        
        while True:
            # Check if slug exists
            query = select(CategoryModel.id).where(CategoryModel.slug == slug)
            result = await self.db.execute(query)
            if not result.scalar_one_or_none():
                return slug
            
            # If it exists, append counter and increment
            slug = f"{base_slug}-{counter}"
            counter += 1
    
    async def _ensure_unique_subcategory_slug(self, base_slug: str) -> str:
        """
        Ensure a subcategory slug is unique by appending a number if necessary.
        
        Args:
            base_slug: Base slug to check
            
        Returns:
            Unique slug
        """
        slug = base_slug
        counter = 1
        
        while True:
            # Check if slug exists
            query = select(SubcategoryModel.id).where(SubcategoryModel.slug == slug)
            result = await self.db.execute(query)
            if not result.scalar_one_or_none():
                return slug
            
            # If it exists, append counter and increment
            slug = f"{base_slug}-{counter}"
            counter += 1
    
    def _generate_slug_from_name(self, name: str) -> str:
        """
        Generate a slug from a name.
        
        Args:
            name: Category or subcategory name
            
        Returns:
            Generated slug
        """
        # This is a simple implementation; a real one would handle special characters better
        slug = name.lower().replace(" ", "-")
        # Remove special characters
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        return slug
    
    def _map_category_to_domain(self, category_model: CategoryModel) -> Category:
        """
        Map category database model to domain entity.
        
        Args:
            category_model: Database model
            
        Returns:
            Domain entity
        """
        return Category(
            id=category_model.id,
            name=category_model.name,
            slug=category_model.slug,
            description=category_model.description,
            icon_url=category_model.icon_url,
            image_url=category_model.image_url,
            position=category_model.position,
            is_active=category_model.is_active,
            created_at=category_model.created_at,
            updated_at=category_model.updated_at
        )
    
    def _map_subcategory_to_domain(self, subcategory_model: SubcategoryModel) -> Subcategory:
        """
        Map subcategory database model to domain entity.
        
        Args:
            subcategory_model: Database model
            
        Returns:
            Domain entity
        """
        return Subcategory(
            id=subcategory_model.id,
            category_id=subcategory_model.category_id,
            name=subcategory_model.name,
            slug=subcategory_model.slug,
            description=subcategory_model.description,
            image_url=subcategory_model.image_url,
            position=subcategory_model.position,
            is_active=subcategory_model.is_active,
            created_at=subcategory_model.created_at,
            updated_at=subcategory_model.updated_at
        ) 