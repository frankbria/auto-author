import { toast as sonnerToast } from "sonner"

export type ToastProps = Omit<
  Parameters<typeof sonnerToast>[1],
  "className" | "duration"
> & {
  title?: string
  description?: string
  duration?: number
  // ponytail: `variant` is a compat shim for the old useToast() contract so its
  // call sites migrate with an import swap. Prefer toast.success/.error directly.
  variant?: "default" | "destructive" | "success"
}

export function toast({
  title,
  description,
  duration = 5000,
  variant = "default",
  ...props
}: ToastProps) {
  const message = title || description || ""
  const descriptionText = title && description ? description : undefined
  const options = { ...props, description: descriptionText, duration }
  switch (variant) {
    case "destructive":
      return sonnerToast.error(message, options)
    case "success":
      return sonnerToast.success(message, options)
    default:
      return sonnerToast(message, options)
  }
}

toast.success = ({
  title = "Success",
  description,
  duration = 4000,
  ...props
}: ToastProps) => {
  return sonnerToast.success(title, {
    ...props,
    description,
    duration,
  })
}

toast.error = ({
  title = "Error",
  description,
  duration = 5000,
  ...props
}: ToastProps) => {
  return sonnerToast.error(title, {
    ...props,
    description,
    duration,
  })
}

toast.warning = ({
  title = "Warning",
  description,
  duration = 5000,
  ...props
}: ToastProps) => {
  return sonnerToast.warning(title, {
    ...props,
    description,
    duration,
  })
}

toast.info = ({
  title = "Info",
  description,
  duration = 4000,
  ...props
}: ToastProps) => {
  return sonnerToast.info(title, {
    ...props,
    description,
    duration,
  })
}

toast.promise = sonnerToast.promise
