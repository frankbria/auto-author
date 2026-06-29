/**
 * Tests for TemplateSelector (issue #59)
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { TemplateSelector } from './TemplateSelector';
import { ExportTemplate } from '@/types/export';

const TEMPLATES: ExportTemplate[] = [
  {
    id: 'classic_fiction',
    name: 'Classic Fiction',
    description: '6x9 trade paperback.',
    category: 'fiction',
    best_for: 'Novels',
    page_size: '6x9',
    margins: { top: 0.75, bottom: 0.75, inside: 0.65, outside: 0.6 },
    font: { family: 'serif', pdf_font: 'Times-Roman', docx_font: 'Garamond', size: 11 },
    line_height: 1.3,
    first_line_indent: 0.2,
    header: { left: '{book_title}', right: '{author}' },
    footer: { center: '{page}' },
  },
  {
    id: 'academic',
    name: 'Academic',
    description: 'Double-spaced A4.',
    category: 'academic',
    best_for: 'Theses',
    page_size: 'A4',
    margins: { top: 1, bottom: 1, inside: 1.25, outside: 1.25 },
    font: { family: 'serif', pdf_font: 'Times-Roman', docx_font: 'Times New Roman', size: 12 },
    line_height: 2,
    first_line_indent: 0.5,
    header: { left: '{book_title}', right: '{author}' },
    footer: { center: '{page}' },
  },
];

describe('TemplateSelector', () => {
  const onSelect = jest.fn();
  const onCustomizationChange = jest.fn();

  beforeEach(() => jest.clearAllMocks());

  it('renders a default option and every template', () => {
    render(<TemplateSelector templates={TEMPLATES} onSelect={onSelect} />);
    expect(screen.getByLabelText(/Default formatting/i)).toBeInTheDocument();
    expect(screen.getByLabelText('Classic Fiction')).toBeInTheDocument();
    expect(screen.getByLabelText('Academic')).toBeInTheDocument();
  });

  it('calls onSelect with the template id when picked', () => {
    render(<TemplateSelector templates={TEMPLATES} onSelect={onSelect} />);
    fireEvent.click(screen.getByLabelText('Academic'));
    expect(onSelect).toHaveBeenCalledWith('academic');
  });

  it('calls onSelect with undefined when default chosen', () => {
    render(
      <TemplateSelector
        templates={TEMPLATES}
        selectedTemplateId="academic"
        onSelect={onSelect}
      />
    );
    fireEvent.click(screen.getByLabelText(/Default formatting/i));
    expect(onSelect).toHaveBeenCalledWith(undefined);
  });

  it('shows a spec preview only when a template is selected', () => {
    const { rerender } = render(
      <TemplateSelector templates={TEMPLATES} onSelect={onSelect} />
    );
    expect(screen.queryByTestId('template-preview')).not.toBeInTheDocument();

    rerender(
      <TemplateSelector
        templates={TEMPLATES}
        selectedTemplateId="classic_fiction"
        onSelect={onSelect}
      />
    );
    const preview = screen.getByTestId('template-preview');
    expect(preview).toHaveTextContent('6x9');
    expect(preview).toHaveTextContent('Garamond');
  });

  it('reveals customization inputs and reports font-size changes', () => {
    render(
      <TemplateSelector
        templates={TEMPLATES}
        selectedTemplateId="classic_fiction"
        onSelect={onSelect}
        customization={{}}
        onCustomizationChange={onCustomizationChange}
      />
    );

    // Hidden until toggled.
    expect(screen.queryByTestId('template-customization')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('customize-toggle'));
    expect(screen.getByTestId('template-customization')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Font size/i), { target: { value: '14' } });
    expect(onCustomizationChange).toHaveBeenCalledWith(
      expect.objectContaining({ font_size: 14 })
    );
  });

  it('preview reflects an active font-size customization', () => {
    render(
      <TemplateSelector
        templates={TEMPLATES}
        selectedTemplateId="classic_fiction"
        onSelect={onSelect}
        customization={{ font_size: 13 }}
      />
    );
    expect(screen.getByTestId('template-preview')).toHaveTextContent('13pt');
  });
});
