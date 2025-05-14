"use client"

import { Toaster as SonnerToaster } from "sonner"

type ToasterProps = React.ComponentProps<typeof SonnerToaster>

export function Toaster({ ...props }: ToasterProps) {
  return (
    <SonnerToaster
      theme="dark"
      className="toaster group"
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-zinc-900 group-[.toaster]:text-zinc-200 group-[.toaster]:border-zinc-700 group-[.toaster]:shadow-lg",
          description: "group-[.toast]:text-zinc-400",
          actionButton:
            "group-[.toast]:bg-indigo-600 group-[.toast]:text-primary-foreground",
          cancelButton:
            "group-[.toast]:bg-zinc-700 group-[.toast]:text-zinc-200",
          success:
            "group-[.toast]:bg-green-900/20 group-[.toast]:border-green-700",
          error: 
            "group-[.toast]:bg-red-900/20 group-[.toast]:border-red-700",
          info: 
            "group-[.toast]:bg-blue-900/20 group-[.toast]:border-blue-700",
          warning: 
            "group-[.toast]:bg-yellow-900/20 group-[.toast]:border-yellow-700",
        },
      }}
      {...props}
    />
  )
}
