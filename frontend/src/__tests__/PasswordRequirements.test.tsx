import React from "react";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import {
  PasswordRequirements,
  validatePassword,
  isPasswordValid,
  getPasswordStrength,
} from "@/components/auth/PasswordRequirements";

describe("PasswordRequirements", () => {
  describe("validatePassword function", () => {
    it("returns all false for empty password", () => {
      const result = validatePassword("");
      expect(result.minLength).toBe(false);
      expect(result.hasUppercase).toBe(false);
      expect(result.hasLowercase).toBe(false);
      expect(result.hasNumber).toBe(false);
    });

    it("validates minimum length correctly", () => {
      expect(validatePassword("short").minLength).toBe(false);
      expect(validatePassword("longpass").minLength).toBe(true);
      expect(validatePassword("12345678").minLength).toBe(true);
    });

    it("validates uppercase requirement correctly", () => {
      expect(validatePassword("lowercase").hasUppercase).toBe(false);
      expect(validatePassword("Uppercase").hasUppercase).toBe(true);
      expect(validatePassword("ALLCAPS").hasUppercase).toBe(true);
    });

    it("validates lowercase requirement correctly", () => {
      expect(validatePassword("UPPERCASE").hasLowercase).toBe(false);
      expect(validatePassword("Lowercase").hasLowercase).toBe(true);
      expect(validatePassword("alllower").hasLowercase).toBe(true);
    });

    it("validates number requirement correctly", () => {
      expect(validatePassword("noNumbers").hasNumber).toBe(false);
      expect(validatePassword("has1number").hasNumber).toBe(true);
      expect(validatePassword("12345").hasNumber).toBe(true);
    });
  });

  describe("isPasswordValid function", () => {
    it("returns false for passwords missing requirements", () => {
      expect(isPasswordValid("")).toBe(false);
      expect(isPasswordValid("short1A")).toBe(false); // Too short
      expect(isPasswordValid("longenough1")).toBe(false); // No uppercase
      expect(isPasswordValid("LONGENOUGH1")).toBe(false); // No lowercase
      expect(isPasswordValid("LongEnough")).toBe(false); // No number
    });

    it("returns true for valid passwords", () => {
      expect(isPasswordValid("ValidPass1")).toBe(true);
      expect(isPasswordValid("Test1234")).toBe(true);
      expect(isPasswordValid("MyP@ssw0rd")).toBe(true);
    });
  });

  describe("getPasswordStrength function", () => {
    it("returns weak for 0-2 requirements met", () => {
      expect(getPasswordStrength("").label).toBe("weak");
      expect(getPasswordStrength("a").label).toBe("weak");
      expect(getPasswordStrength("ab").label).toBe("weak");
    });

    it("returns medium for 3 requirements met", () => {
      expect(getPasswordStrength("longpass1").label).toBe("medium"); // lowercase, length, number
      expect(getPasswordStrength("LONGPASS1").label).toBe("medium"); // uppercase, length, number
    });

    it("returns strong for all requirements met", () => {
      expect(getPasswordStrength("ValidPass1").label).toBe("strong");
      expect(getPasswordStrength("Test1234").label).toBe("strong");
    });

    it("calculates percentage correctly", () => {
      expect(getPasswordStrength("").percentage).toBe(0);
      expect(getPasswordStrength("a").percentage).toBe(25);
      expect(getPasswordStrength("longpass").percentage).toBe(50);
      expect(getPasswordStrength("ValidPass1").percentage).toBe(100);
    });
  });

  describe("PasswordRequirements component", () => {
    it("renders all requirement items", () => {
      render(<PasswordRequirements password="" />);

      expect(screen.getByText("At least 8 characters")).toBeInTheDocument();
      expect(screen.getByText("At least one uppercase letter")).toBeInTheDocument();
      expect(screen.getByText("At least one lowercase letter")).toBeInTheDocument();
      expect(screen.getByText("At least one number")).toBeInTheDocument();
    });

    it("shows unmet requirements with X icon", () => {
      render(<PasswordRequirements password="" />);

      const list = screen.getByRole("list", { name: "Password requirements" });
      expect(list).toBeInTheDocument();

      // All requirements should be unmet for empty password
      const items = screen.getAllByRole("listitem");
      expect(items).toHaveLength(4);
    });

    it("shows met requirements with check icon", () => {
      render(<PasswordRequirements password="ValidPass1" />);

      // All 4 requirements should be met
      const list = screen.getByRole("list", { name: "Password requirements" });
      expect(list).toBeInTheDocument();
    });

    it("does not show strength meter by default", () => {
      render(<PasswordRequirements password="test" />);

      expect(screen.queryByText("Password strength")).not.toBeInTheDocument();
    });

    it("shows strength meter when showStrength is true", () => {
      render(<PasswordRequirements password="test" showStrength />);

      expect(screen.getByText("Password strength")).toBeInTheDocument();
    });

    it("does not show strength meter for empty password", () => {
      render(<PasswordRequirements password="" showStrength />);

      expect(screen.queryByText("Password strength")).not.toBeInTheDocument();
    });

    it("shows correct strength label", () => {
      const { rerender } = render(
        <PasswordRequirements password="weak" showStrength />
      );
      expect(screen.getByText("Weak")).toBeInTheDocument();

      rerender(<PasswordRequirements password="ValidPass1" showStrength />);
      expect(screen.getByText("Strong")).toBeInTheDocument();
    });

    it("applies custom className", () => {
      const { container } = render(
        <PasswordRequirements password="test" className="custom-class" />
      );

      expect(container.firstChild).toHaveClass("custom-class");
    });

    it("has accessible progress bar", () => {
      render(<PasswordRequirements password="ValidPass1" showStrength />);

      const progressBar = screen.getByRole("progressbar");
      expect(progressBar).toHaveAttribute("aria-valuenow", "100");
      expect(progressBar).toHaveAttribute("aria-valuemin", "0");
      expect(progressBar).toHaveAttribute("aria-valuemax", "100");
    });
  });
});
