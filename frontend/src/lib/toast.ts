import { toast as sonnerToast } from "sonner"

export type ToastProps = Omit<
  Parameters<typeof sonnerToast>[1],
  "className" | "duration"
> & {
  title?: string
  description?: string
  duration?: number
}

export function toast({
  title,
  description,
  duration = 5000,
  ...props
}: ToastProps) {
  return sonnerToast(title, {
    ...props,
    description,
    duration,
  })
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
