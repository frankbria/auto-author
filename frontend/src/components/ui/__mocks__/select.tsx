/**
 * Mock implementation of Radix UI Select for testing
 * Radix UI Select uses portals which don't work in jsdom
 * This mock provides a simple HTML <select> for unit tests
 */

import * as React from 'react';

export const Select = ({ children, value, onValueChange, ...props }: any) => {
  return (
    <div data-testid="select-root" {...props}>
      {React.Children.map(children, (child) => {
        if (child?.type?.displayName === 'SelectTrigger') {
          return React.cloneElement(child, { value, onValueChange });
        }
        return child;
      })}
    </div>
  );
};

export const SelectGroup = ({ children }: any) => children;

export const SelectValue = ({ placeholder }: any) => <span>{placeholder}</span>;

export const SelectTrigger = React.forwardRef(
  ({ children, value, onValueChange, ...props }: any, ref: any) => {
    const selectRef = React.useRef<HTMLSelectElement>(null);

    React.useImperativeHandle(ref, () => selectRef.current!);

    const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
      onValueChange?.(e.target.value);
    };

    return (
      <div>
        <select
          ref={selectRef}
          value={value}
          onChange={handleChange}
          aria-label={props['aria-label']}
          {...props}
        >
          <option value="">{children}</option>
        </select>
      </div>
    );
  }
);
SelectTrigger.displayName = 'SelectTrigger';

export const SelectContent = ({ children }: any) => children;

export const SelectItem = ({ value, children }: any) => {
  return <option value={value}>{children}</option>;
};

export const SelectScrollUpButton = () => null;
export const SelectScrollDownButton = () => null;
