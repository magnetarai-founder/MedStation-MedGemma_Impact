/**
 * T3-2: VisibilityBadge Component
 *
 * Displays workflow visibility (personal/team/global) with consistent styling,
 * icons, and tooltips across the application.
 */

import React from 'react';
import { WorkflowVisibility } from '../../../types/workflow';
import { User, Users, Globe } from 'lucide-react';

interface VisibilityBadgeProps {
  visibility: WorkflowVisibility | undefined;
  className?: string;
  showIcon?: boolean;
  showTooltip?: boolean;
}

const VisibilityBadge: React.FC<VisibilityBadgeProps> = ({
  visibility = 'personal',
  className = '',
  showIcon = true,
  showTooltip = true,
}) => {
  // Default to 'personal' if undefined (backward compatibility)
  const resolvedVisibility = visibility || 'personal';

  const config = {
    personal: {
      label: 'Personal',
      icon: User,
      bgColor: 'bg-blue-100 dark:bg-blue-900/30',
      textColor: 'text-blue-800 dark:text-blue-200',
      borderColor: 'border-blue-200 dark:border-blue-800',
      tooltip: 'Visible only to you. Work items in this workflow are private.',
    },
    team: {
      label: 'Team',
      icon: Users,
      bgColor: 'bg-purple-100 dark:bg-purple-900/30',
      textColor: 'text-purple-800 dark:text-purple-200',
      borderColor: 'border-purple-200 dark:border-purple-800',
      tooltip: 'Visible to members of your team. Work items are shared within your team.',
    },
    global: {
      label: 'Global',
      icon: Globe,
      bgColor: 'bg-amber-100 dark:bg-amber-900/30',
      textColor: 'text-amber-800 dark:text-amber-200',
      borderColor: 'border-amber-200 dark:border-amber-800',
      tooltip: 'System workflow visible to all users with workflow access.',
    },
  };

  const { label, icon: Icon, bgColor, textColor, borderColor, tooltip } = config[resolvedVisibility];

  return (
    <span
      className={`
        inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium
        border
        ${bgColor} ${textColor} ${borderColor}
        ${className}
      `}
      title={showTooltip ? tooltip : undefined}
      aria-label={`Visibility: ${label}`}
    >
      {showIcon && <Icon className="w-3 h-3" aria-hidden="true" />}
      <span>{label}</span>
    </span>
  );
};

export default VisibilityBadge;
