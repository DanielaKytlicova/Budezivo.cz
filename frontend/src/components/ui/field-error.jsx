import * as React from "react"

export const FIELD_ERROR_CLASS = "border-red-500 ring-1 ring-red-500 focus-visible:ring-red-500"

const FieldError = React.forwardRef(({ className = "", message, ...props }, ref) => {
  if (!message) return null
  return (
    <p
      ref={ref}
      className={`mt-1 text-sm text-red-600 ${className}`.trim()}
      {...props}
    >
      {message}
    </p>
  )
})

FieldError.displayName = "FieldError"

export { FieldError }
