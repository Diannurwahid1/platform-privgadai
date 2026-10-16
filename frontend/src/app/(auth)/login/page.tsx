"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { motion } from "framer-motion";
import { login } from "@/lib/auth";
import { loginSchema } from "@/lib/validators";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Field, FieldError } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { AuthOptions } from "@/components/auth-options";
import type { ApiError } from "@/lib/api";

type FieldErrors = Partial<Record<"email" | "password" | "mfa_code" | "form", string>>;

export default function LoginPage() {
  const router = useRouter();
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrors({});
    const data = new FormData(event.currentTarget);
    const parsed = loginSchema.safeParse({
      email: data.get("email"),
      password: data.get("password"),
      mfa_code: String(data.get("mfa_code") ?? "") || undefined,
    });
    if (!parsed.success) {
      const fieldErrors: FieldErrors = {};
      for (const issue of parsed.error.issues) {
        fieldErrors[issue.path[0] as keyof FieldErrors] = issue.message;
      }
      setErrors(fieldErrors);
      return;
    }

    setSubmitting(true);
    try {
      await login(parsed.data);
      router.push("/dashboard");
      router.refresh();
    } catch (err) {
      const apiErr = err as ApiError;
      setErrors({ form: apiErr.detail ?? "Email atau kata sandi tidak dapat diverifikasi." });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="w-full"
    >
      <Card>
        <CardHeader>
          <CardTitle>Masuk ke PrivGadai</CardTitle>
          <CardDescription>
            Lanjutkan setup tenant atau pekerjaan operasional cabang Anda.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Field>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
              />
              <FieldError>{errors.email}</FieldError>
            </Field>
            <Field>
              <Label htmlFor="password">Kata sandi</Label>
              <Input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
              />
              <FieldError>{errors.password}</FieldError>
            </Field>
            <Field>
              <Label htmlFor="mfa_code">Kode MFA (opsional)</Label>
              <Input
                id="mfa_code"
                name="mfa_code"
                inputMode="numeric"
                autoComplete="one-time-code"
                placeholder="Isi jika MFA sudah diaktifkan"
              />
              <FieldError>{errors.mfa_code}</FieldError>
            </Field>
            <FieldError>{errors.form}</FieldError>
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? "Memverifikasi…" : "Masuk"}
            </Button>
          </form>
          <AuthOptions />
        </CardContent>
      </Card>
      <p className="mt-4 text-center text-sm text-muted-foreground">
        Belum punya akun?{" "}
        <Link
          href="/register"
          className="font-medium text-primary hover:underline"
        >
          Buat akun
        </Link>
        {" · "}
        <Link
          href="/forgot-password"
          className="font-medium text-primary hover:underline"
        >
          Lupa kata sandi?
        </Link>
      </p>
    </motion.div>
  );
}
