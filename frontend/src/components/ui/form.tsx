"use client"

import * as React from "react"
import {
  useForm,
  Controller,
  type ControllerProps,
  type ControllerRenderProps,
  type FieldPath,
  type FieldValues,
  FormProvider,
  UseFormProps,
  UseFormReturn,
} from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { cn } from "@/lib/utils"
import { Label } from "@/components/ui/label"

interface FormProps<TFieldValues extends FieldValues> {
  form: UseFormReturn<TFieldValues>
  children: React.ReactNode
  className?: string
  onSubmit?: (data: TFieldValues) => void
}

function Form<TFieldValues extends FieldValues>({
  form,
  children,
  className,
  onSubmit,
}: FormProps<TFieldValues>) {
  return (
    <FormProvider {...form}>
      <form
        onSubmit={onSubmit ? form.handleSubmit(onSubmit) : undefined}
        className={cn("space-y-6", className)}
      >
        {children}
      </form>
    </FormProvider>
  )
}

type FormFieldContextValue<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
> = {
  name: TName
}

const FormFieldContext = React.createContext<FormFieldContextValue>(
  {} as FormFieldContextValue
)

const useFormField = () => {
  const fieldContext = React.useContext(FormFieldContext)

  if (!fieldContext) {
    throw new Error("useFormField should be used within <FormField>")
  }

  return fieldContext
}

interface FormFieldProps<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
> {
  name: TName
  control?: ControllerProps<TFieldValues, TName>["control"]
  render: (field: {
    field: ControllerRenderProps<TFieldValues, TName>
    formState: UseFormReturn<TFieldValues>["formState"]
  }) => React.ReactNode
  className?: string
  label?: string
  description?: string
}

function FormField<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
>({
  name,
  control,
  render,
  className,
  label,
  description,
}: FormFieldProps<TFieldValues, TName>) {
  const { formState } = useForm<TFieldValues>()
  
  return (
    <FormFieldContext.Provider value={{ name }}>
      <Controller
        name={name}
        control={control}
        render={({ field }) => (
          <div className={cn("space-y-2", className)}>
            {label && <Label htmlFor={name}>{label}</Label>}
            {render({ field, formState })}
            {description && (
              <p className="text-sm text-zinc-500">{description}</p>
            )}
            {formState.errors[name]?.message && (
              <p className="text-sm text-red-500">
                {formState.errors[name]?.message as string}
              </p>
            )}
          </div>
        )}
      />
    </FormFieldContext.Provider>
  )
}

export { 
  useForm, 
  Form, 
  FormField, 
  useFormField,
  zodResolver,
  z
}
