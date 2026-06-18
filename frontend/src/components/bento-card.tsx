import * as React from "react"
import { cn } from "@/lib/utils"

interface BentoCardProps extends React.HTMLAttributes<HTMLDivElement> {
    size?: "1x1" | "1x2" | "2x1" | "2x2"
    glassmorphism?: boolean
    tilt?: boolean
}

const sizeClasses = {
    "1x1": "col-span-1 row-span-1",
    "1x2": "col-span-1 row-span-2",
    "2x1": "col-span-2 row-span-1",
    "2x2": "col-span-2 row-span-2",
}

export const BentoCard = React.forwardRef<HTMLDivElement, BentoCardProps>(
    ({ className, size = "1x1", glassmorphism = false, tilt = true, children, ...props }, ref) => {
        return (
            <div
                ref={ref}
                className={cn(
                    "rounded-2xl border p-6 transition-all duration-300",
                    sizeClasses[size],
                    glassmorphism
                        ? "glass-card border-white/10"
                        : "bg-card border-border shadow-soft hover:shadow-medium",
                    tilt && "tilt-card hover:scale-[1.01] hover:-translate-y-1",
                    "relative overflow-hidden group",
                    className
                )}
                {...props}
            >
                {/* Animated border on hover */}
                <div className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none">
                    <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-primary/20 via-accent/20 to-primary/20 animate-pulse" />
                </div>

                {/* Subtle Background Gradient */}
                <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />

                {/* Content */}
                <div className="relative z-10 flex flex-col h-full">
                    {children}
                </div>
            </div>
        )
    }
)

BentoCard.displayName = "BentoCard"
