import * as React from "react"
import { cn } from "@/lib/utils"
import type { LucideIcon } from "lucide-react"

interface StatCardProps extends React.HTMLAttributes<HTMLDivElement> {
    label: string
    value: string | number
    icon?: LucideIcon
    trend?: "up" | "down" | "neutral"
    trendValue?: string
    animated?: boolean
    variant?: "default" | "ghost"
    iconColor?: string
    iconBgColor?: string
}

export const StatCard = React.forwardRef<HTMLDivElement, StatCardProps>(
    ({ className, label, value, icon: Icon, trend, trendValue, animated = true, variant = "default", iconColor, iconBgColor, ...props }, ref) => {
        const [displayValue, setDisplayValue] = React.useState(0)
        const numericValue = typeof value === 'number' ? value : parseFloat(value) || 0

        React.useEffect(() => {
            if (!animated || typeof value !== 'number') return

            const duration = 2000 // 2 seconds
            const steps = 60
            const increment = numericValue / steps
            let current = 0

            const timer = setInterval(() => {
                current += increment
                if (current >= numericValue) {
                    setDisplayValue(numericValue)
                    clearInterval(timer)
                } else {
                    setDisplayValue(Math.floor(current))
                }
            }, duration / steps)

            return () => clearInterval(timer)
        }, [value, animated, numericValue])

        return (
            <div
                ref={ref}
                className={cn(
                    "rounded-2xl p-6 transition-all duration-300 group",
                    variant === "default"
                        ? "border border-border bg-card shadow-soft hover:shadow-medium tilt-card hover:scale-[1.02]"
                        : "bg-transparent hover:bg-white/5",
                    className
                )}
                {...props}
            >
                <div className="flex items-start justify-between mb-4">
                    <span className="text-sm text-muted-foreground font-medium">{label}</span>
                    {Icon && (
                        <div
                            className={cn(
                                "p-2 rounded-lg transition-transform duration-300 group-hover:scale-110",
                                !iconBgColor && "bg-primary/10 text-primary"
                            )}
                            style={{
                                backgroundColor: iconBgColor,
                                color: iconColor
                            }}
                        >
                            <Icon className="w-5 h-5" />
                        </div>
                    )}
                </div>

                <div className="space-y-2">
                    <div className="text-3xl font-bold bg-gradient-to-r from-foreground to-foreground/60 bg-clip-text text-transparent">
                        {animated && typeof value === 'number' ? displayValue.toLocaleString() : value}
                    </div>

                    {trend && trendValue && (
                        <div className={cn(
                            "flex items-center gap-1 text-sm font-medium",
                            trend === "up" ? "text-green-500" : trend === "down" ? "text-red-500" : "text-muted-foreground"
                        )}>
                            <span>{trend === "up" ? "↑" : trend === "down" ? "↓" : "•"}</span>
                            <span>{trendValue}</span>
                        </div>
                    )}
                </div>
            </div>
        )
    }
)

StatCard.displayName = "StatCard"
