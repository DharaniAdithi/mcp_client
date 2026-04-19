import logging
from typing import List

from langchain_core.messages import HumanMessage, ToolMessage
from langchain.tools import tool, ToolRuntime
from langgraph.types import Command, interrupt
from langgraph.errors import GraphInterrupt

from src.agent.quiz_agent import QuizGeneratorAgent
from src.agent.review_agent import ReviewAgent
from src.models.models import QuizState
from src.utils.error_codes import QuizGenerationError, QuizEvaluationError

logger = logging.getLogger(__name__)


def _extract_numbered_questions(raw_text: str) -> List[str]:
    """
    Extract numbered questions from raw LLM output.

    Filters out non-question lines and returns only lines that start
    with a digit (indicating a numbered question).

    Args:
        raw_text: Raw text output from the LLM.

    Returns:
        List[str]: List of extracted questions.
    """
    lines = raw_text.strip().splitlines()
    questions = [
        line.strip()
        for line in lines
        if line.strip() and line.strip()[0].isdigit()
    ]
    return questions


@tool
async def generate_quiz(
    user_query: str,
    runtime: ToolRuntime[None, QuizState],
) -> Command:
    """
    Generate quiz questions on a given topic.

    On first call: generates questions and interrupts for user answers.
    On resume call: answers are already in state — skips generation and
    interrupt, returns existing questions and answers immediately.

    Args:
        user_query: Topic or subject for quiz generation.
        runtime: LangGraph tool runtime context with state access.

    Returns:
        Command: State update command with questions and answers.

    Raises:
        QuizGenerationError: If question generation fails.
    """
    try:
        num_questions = runtime.state.get("num_questions", 3)
        difficulty = runtime.state.get("difficulty", "medium")
        existing_answers = runtime.state.get("answers", [])
        existing_questions = runtime.state.get("questions", [])

        if existing_answers and existing_questions:
            logger.info(
                f"Answers already collected ({len(existing_answers)}) — "
                f"skipping generation and interrupt, forwarding to evaluator"
            )
            return Command(
                update={
                    "messages": [
                        ToolMessage(
                            content=(
                                f"Questions and answers already available — "
                                f"forwarding {len(existing_questions)} Q&A pairs"
                            ),
                            tool_call_id=runtime.tool_call_id,
                        )
                    ],
                    "questions": existing_questions,
                    "answers": existing_answers,
                    "current_step": "answer_evaluator",
                }
            )

        logger.info(f"Starting quiz generation for topic: {user_query}")
        logger.debug(
            f"Quiz parameters - questions={num_questions}, difficulty={difficulty}"
        )

        generator = await QuizGeneratorAgent.get_instance()

        generation_prompt = (
            f"Topic: {user_query}\n"
            f"Generate exactly {num_questions} {difficulty}-difficulty questions.\n"
            f"Number each question like: 1, 2, 3, etc.\n"
            f"Output ONLY the numbered questions, no preamble."
        )

        response = await generator.agent.ainvoke(
            {"messages": [HumanMessage(content=generation_prompt)]}
        )

        raw_response = response["messages"][-1].content
        questions = _extract_numbered_questions(raw_response)
        questions = questions[:num_questions]

        logger.info(f"Generated {len(questions)} questions successfully")

        user_answers = interrupt({
            "type": "quiz",
            "questions": questions,
            "num_questions": num_questions,
            "difficulty": difficulty,
        })

        logger.debug(f"Collected {len(user_answers)} user answers")

        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=(
                            f"Generated {len(questions)} questions "
                            f"and collected {len(user_answers)} answers"
                        ),
                        tool_call_id=runtime.tool_call_id,
                    )
                ],
                "questions": questions,
                "answers": user_answers,
                "current_step": "answer_evaluator",
            }
        )

    except GraphInterrupt:
        raise

    except QuizGenerationError:
        raise

    except Exception as generation_error:
        logger.error(
            f"Quiz generation failed: {generation_error}",
            exc_info=True
        )
        raise QuizGenerationError(
            message="Failed to generate quiz questions",
            original_exception=generation_error
        )


@tool
async def evaluate_answers(
    user_query: str,
    runtime: ToolRuntime[None, QuizState],
) -> Command:
    """
    Evaluate user answers and provide feedback.

    Args:
        user_query: Original quiz topic for context.
        runtime: LangGraph tool runtime context with state access.

    Returns:
        Command: State update command with evaluation feedback.

    Raises:
        QuizEvaluationError: If answer evaluation fails.
    """
    try:
        logger.info("Starting quiz answer evaluation")

        questions = runtime.state.get("questions", [])
        answers = runtime.state.get("answers", [])
        num_questions = runtime.state.get("num_questions", len(questions))
        difficulty = runtime.state.get("difficulty", "medium")

        logger.debug(
            f"Evaluation parameters - "
            f"questions={len(questions)}, answers={len(answers)}, "
            f"difficulty={difficulty}"
        )

        if len(questions) != len(answers):
            logger.warning(
                f"Question/answer mismatch: {len(questions)} questions, "
                f"{len(answers)} answers"
            )

        evaluator = await ReviewAgent.get_instance()

        qa_pairs = "\n\n".join(
            f"Q{i+1} [{difficulty}]: {question}\nUser answer: {answer}"
            for i, (question, answer) in enumerate(zip(questions, answers))
        )

        evaluation_prompt = (
            f"Topic: {user_query}\n"
            f"Difficulty: {difficulty} | Total questions: {num_questions}\n\n"
            f"Evaluate each answer. For each question provide:\n"
            f"- Verdict (correct/partial/incorrect)\n"
            f"- Correct answer\n"
            f"- Explanation\n"
            f"- Study tip\n\n"
            f"{qa_pairs}\n\n"
            f"End with: Overall score: X/{num_questions}"
        )

        response = await evaluator.agent.ainvoke(
            {"messages": [HumanMessage(content=evaluation_prompt)]}
        )

        feedback = response["messages"][-1].content

        logger.info("Quiz evaluation completed successfully")
        logger.debug(f"Feedback length: {len(feedback)} characters")

        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=feedback,        
                        tool_call_id=runtime.tool_call_id,
                    )
                ],
                "feedback": str(feedback),
                "current_step": "question_generator",
            }
        )

    except QuizEvaluationError:
        raise

    except Exception as evaluation_error:
        logger.error(
            f"Quiz evaluation failed: {evaluation_error}",
            exc_info=True
        )
        raise QuizEvaluationError(
            message="Failed to evaluate quiz answers",
            original_exception=evaluation_error
        )