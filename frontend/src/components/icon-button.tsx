import React from 'react';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon: React.ReactNode;
  label: string;
  variant?: 'ghost' | 'outline' | 'destructive';
  size?: 'default' | 'sm' | 'lg';
}

/**
 * Reusable icon-only button with tooltip.
 * Used for sidebar toggle, delete thread, close inspector, copy message, etc.
 */
export const IconButton: React.FC<IconButtonProps> = ({
  icon,
  label,
  variant = 'ghost',
  size = 'default',
  className,
  ...props
}) => {
  const sizeMap = {
    sm: 'icon-sm' as const,
    default: 'icon' as const,
    lg: 'icon-lg' as const,
  };

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant={variant}
          size={sizeMap[size]}
          className={cn(
            'text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors',
            className,
          )}
          aria-label={label}
          {...props}
        >
          {icon}
        </Button>
      </TooltipTrigger>
      <TooltipContent side="bottom" className="text-xs">
        {label}
      </TooltipContent>
    </Tooltip>
  );
};
