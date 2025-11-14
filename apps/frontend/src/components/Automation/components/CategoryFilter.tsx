import { CATEGORY_OPTIONS } from '../shared/categories'
import type { TemplateCategory } from '../shared/categories'

interface CategoryFilterProps {
  selectedCategory: TemplateCategory | 'all'
  onCategoryChange: (category: TemplateCategory | 'all') => void
}

export function CategoryFilter({ selectedCategory, onCategoryChange }: CategoryFilterProps) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      <button
        onClick={() => onCategoryChange('all')}
        className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
          selectedCategory === 'all'
            ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 border border-primary-300 dark:border-primary-700'
            : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:bg-gray-200 dark:hover:bg-gray-700'
        }`}
      >
        All
      </button>
      {CATEGORY_OPTIONS.map((category) => (
        <button
          key={category.value}
          onClick={() => onCategoryChange(category.value as TemplateCategory)}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors flex items-center gap-1.5 ${
            selectedCategory === category.value
              ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 border border-primary-300 dark:border-primary-700'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:bg-gray-200 dark:hover:bg-gray-700'
          }`}
        >
          <span>{category.emoji}</span>
          <span>{category.label}</span>
        </button>
      ))}
    </div>
  )
}
