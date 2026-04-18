from langchain_core.messages import HumanMessage
from langchain.messages import ToolMessage
from langchain.tools import tool, ToolRuntime
from langgraph.types import Command, interrupt
from agent.quiz_agent import QuizGeneratorAgent   
from agent.review_agent import ReviewAgent   
from models.models import QuizState
import logging

logger = logging.getLogger(__name__)

# SQ 1.33 - 1.49 : Read num_questions and difficulty from runtime, Get QuizGeneratorAgent singleton via get_instance, Build prompt_content with user_query, num_questions and difficulty, Invoke generator_agent with prompt_content, Parse response splitlines and filter numbered question lines, Truncate questions list to num_questions hard cap, Call interrupt with type, questions, num_questions, difficulty, Graph PAUSES here  state persisted to Postgres, Graph resumes interrupt returns user_answers list, Return Command updating questions, answers, current_step is answer_evaluator

@tool
async def generate_quiz(
    user_query: str,
    runtime: ToolRuntime[None, QuizState],
):
    """Generate quiz questions on the topic, then collect user answers via interrupt."""
    try:
        logger.info("generate_quiz tool called")

        num_questions = runtime.state.get("num_questions") or 3
        difficulty= runtime.state.get("difficulty") or "medium"

        logger.info(f"generate_quiz | n={num_questions} diff={difficulty}")
        generator = await QuizGeneratorAgent.get_instance()
        prompt_content = (
            f"user query: {user_query}\n"
            f"Generate exactly {num_questions} {difficulty}-difficulty questions.\n"
            f"Number each question like: 1,2,3,etc."
        )

        response  = await generator.generator_agent.ainvoke(
            {"messages": [HumanMessage(content=prompt_content)]}
        )
        raw_lines = response["messages"][-1].content.strip().splitlines()
        questions = [
            line.strip()
            for line in raw_lines
            if line.strip() and line.strip()[0].isdigit()
        ]
        questions = questions[:num_questions] 

        logger.info(f"generate_quiz - generated {len(questions)} questions")
        user_answers = interrupt({
            "type": "quiz",
            "questions": questions,
            "num_questions": num_questions,   
            "difficulty": difficulty,   
        })

        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"Questions: {questions} | Answers: {user_answers}",
                        tool_call_id=runtime.tool_call_id,
                    )
                ],
                "questions": questions,
                "answers": user_answers,
                "current_step": "answer_evaluator", 
            }
        )

    except Exception as e:
        logger.error(f"generate_quiz error: {e}")
        raise


# SQ 1.64 - SQ 1.79 : Get ReviewAgent singleton via get_instance(), Read questions, answers, num_questions, difficulty from runtime state, Build qa_block joining Q&A pairs with difficulty label per question, Build prompt_content with qa_block, verdict instructions and score format, Invoke evaluator_agent with prompt_content, Extract feedback string from last message in response, Return Command updating feedback 
 
@tool
async def evaluate_answers(
    user_query: str,
    runtime: ToolRuntime[None, QuizState],
):
    """Evaluate the user's answers and return detailed feedback."""
    try:
        logger.info("evaluate_answers tool called")

        evaluator = await ReviewAgent.get_instance()  
        questions = runtime.state.get("questions") or []
        answers = runtime.state.get("answers") or []
        num_questions = runtime.state.get("num_questions") or len(questions)
        difficulty = runtime.state.get("difficulty") or "medium"

        logger.info(f"evaluate_answers - {len(questions)} Qs, {len(answers)} As")

        qa_block = "\n\n".join(
            f"Q{i+1} [{difficulty}]: {q}\nUser answer: {a}"
            for i, (q, a) in enumerate(zip(questions, answers))
        )

        prompt_content = (
            f"user query: {user_query}\n"
            f"Difficulty: {difficulty} | Total questions: {num_questions}\n\n"
            f"Evaluate each answer below and give a verdict "
            f"(correct / partial / incorrect), correct answer, explanation, and tip.\n\n"
            f"{qa_block}\n\n"
            f"End with: Overall score: X/{num_questions}"
        )

        response = await evaluator.evaluator_agent.ainvoke(  
            {"messages": [HumanMessage(content=prompt_content)]}
        )
        feedback = response["messages"][-1].content

        logger.info(f"evaluate_answers - feedback received")

        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"Feedback: {feedback}",
                        tool_call_id=runtime.tool_call_id,
                    )
                ],
                "feedback": str(feedback), 
                "current_step": "question_generator", 
            }
        )

    except Exception as e:
        logger.error(f"evaluate_answers error: {e}")
        raise