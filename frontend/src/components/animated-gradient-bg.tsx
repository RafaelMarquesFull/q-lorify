import * as React from "react"
import { cn } from "@/lib/utils"

interface AnimatedGradientBgProps extends React.HTMLAttributes<HTMLDivElement> {
    variant?: "default" | "subtle" | "intense"
}

export const AnimatedGradientBg: React.FC<AnimatedGradientBgProps> = ({
    className,
    variant = "default",
    children,
    ...props
}) => {
    const variantClasses = {
        default: "opacity-20",
        subtle: "opacity-10",
        intense: "opacity-35"
    }

    return (
        <div className={cn("relative", className)} {...props}>
            {/* Static mesh gradient background — no animations for performance */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                {/* Primary gradient blob */}
                <div
                    className={cn(
                        "absolute w-[400px] h-[400px] rounded-full blur-[80px]",
                        "bg-gradient-to-r from-primary to-primary/50",
                        variantClasses[variant]
                    )}
                    style={{
                        top: '-10%',
                        left: '-5%',
                        willChange: 'auto',
                    }}
                />

                {/* Accent gradient blob */}
                <div
                    className={cn(
                        "absolute w-[400px] h-[400px] rounded-full blur-[80px]",
                        "bg-gradient-to-r from-accent to-accent/50",
                        variantClasses[variant]
                    )}
                    style={{
                        bottom: '-10%',
                        right: '-5%',
                        willChange: 'auto',
                    }}
                />
            </div>

            {/* Content */}
            <div className="relative z-10">
                {children}
            </div>
        </div>
    )
}

AnimatedGradientBg.displayName = "AnimatedGradientBg"
