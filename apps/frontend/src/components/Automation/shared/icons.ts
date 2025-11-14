import { FileText, Users, Heart, Calendar, UserPlus, DollarSign, BookOpen, Plane } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export const WORKFLOW_ICONS: Record<string, LucideIcon> = {
  'clinic-intake': FileText,
  'worship-planning': Users,
  'visitor-followup': UserPlus,
  'small-group-coordinator': Users,
  'prayer-request-router': Heart,
  'event-manager': Calendar,
  'donation-tracker': DollarSign,
  'volunteer-scheduler': Calendar,
  'curriculum-builder': BookOpen,
  'sunday-school-coordinator': BookOpen,
  'trip-planner': Plane,
}
