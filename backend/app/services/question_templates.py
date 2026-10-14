"""What the chapter interview asks about in a non-fiction book (#835).

The question types are named for fiction (character, plot, setting) and are
stored on every question, so the names stay. What each one asks about in a
non-fiction chapter is here: the hint given to the model, the questions used
when the model returns nothing usable, and the help shown with them.
"""

from typing import Dict, List

from app.schemas.book import QuestionType

FOCUS_HINTS = {
    QuestionType.CHARACTER: "the people in the chapter: the reader it is for and those whose experience or work it draws on",
    QuestionType.PLOT: "the chapter's structure: its main point and the order of its ideas and how it reaches its conclusion",
    QuestionType.SETTING: "context: the situation the chapter applies to and the background a reader needs",
    QuestionType.THEME: "the chapter's message: the idea a reader should take away and how it serves the book's argument",
    QuestionType.RESEARCH: "evidence: the sources and facts and terms that need checking or explaining",
}


def fallback_templates(chapter_title: str) -> Dict[QuestionType, List[str]]:
    return {
        QuestionType.CHARACTER: [
            "Who is this chapter written for, and what do they already know about its subject?",
            "Whose experience, yours or someone else's, best shows why this chapter matters?",
            "Who are the people a reader will meet in this chapter, and what does each one show?",
            "What does the reader want, or worry about, when they arrive at this chapter?",
            "Whose work or thinking does this chapter build on, and how should they be credited?",
        ],
        QuestionType.PLOT: [
            f"What is the main point of {chapter_title}, in one or two sentences?",
            "What are the steps a reader has to follow to get from the start of this chapter to its conclusion?",
            "What question does this chapter open with, and how has it answered it by the end?",
            "What is the hardest part of this chapter to explain, and where in the chapter should it come?",
            "How does this chapter follow from the one before it and prepare for the one after?",
        ],
        QuestionType.SETTING: [
            "In what situation would a reader use what this chapter teaches?",
            "What background does a reader need before this chapter makes sense?",
            "When and where did the events or findings in this chapter take place, and does that change how to read them?",
            "What has changed in this field recently that a reader should know before reading this chapter?",
            "What would a reader in a different industry or country need to have explained?",
        ],
        QuestionType.THEME: [
            "What is the one idea a reader should still remember from this chapter a month later?",
            "What common belief does this chapter challenge?",
            "How does this chapter support the argument of the book as a whole?",
            "What will a sceptical reader object to, and how do you answer them?",
            "What should a reader do differently after reading this chapter?",
        ],
        QuestionType.RESEARCH: [
            "What evidence supports the main claim of this chapter?",
            "Which facts, figures or quotations in this chapter need a source?",
            "What studies, books or experts should this chapter cite?",
            "Which terms in this chapter need defining for a general reader?",
            "What is still uncertain or disputed about this chapter's subject, and how will you say so?",
        ],
    }


FALLBACK_HELP = {
    QuestionType.CHARACTER: {
        "help_text": "Think of one real reader, and of the people whose experience makes the point.",
        "examples": ["A first-time manager who has just inherited a team of eight"],
    },
    QuestionType.PLOT: {
        "help_text": "Set out the order of ideas: what comes first, what depends on it, and where the chapter ends.",
        "examples": ["Start with the failed launch, explain its three causes, and end with the checklist"],
    },
    QuestionType.SETTING: {
        "help_text": "Give the circumstances a reader needs: when, where and for whom this applies.",
        "examples": ["This applies to companies of fewer than fifty people; larger ones have a different problem"],
    },
    QuestionType.THEME: {
        "help_text": "Name the idea in a sentence a reader could repeat to someone else.",
        "examples": ["Small changes repeated daily beat large ones attempted once"],
    },
    QuestionType.RESEARCH: {
        "help_text": "List what has to be checked or sourced before a reader can rely on it.",
        "examples": ["The 40% figure comes from a 2019 survey and needs its source and sample size"],
    },
}
