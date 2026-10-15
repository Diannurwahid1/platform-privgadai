"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full text-sm font-semibold tracking-tight transition-[transform,box-shadow,background-color] duration-300 ease-[var(--pg-ease)] hover:-translate-y-0.5 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-60 disabled:hover:translate-y-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
  {
    variants: {
      variant: {
        primary:
          "bg-[linear-gradient(135deg,var(--pg-blue-600),var(--pg-blue-500))] text-primary-foreground shadow-[0_10px_25px_rgba(31,104,247,0.28)] hover:shadow-[0_14px_32px_rgba(31,104,247,0.34)]",
        secondary:
          "border border-border bg-surface text-foreground shadow-[var(--pg-shadow-sm)] hover:bg-muted",
        ghost: "hover:bg-muted text-foreground",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90",
      },
      size: {
        sm: "h-9 px-3",
        md: "h-10 px-4",
        lg: "h-11 px-6 text-base",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps
  extends
    React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  ),
);
Button.displayName = "Button";
