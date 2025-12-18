import json
import os
import asyncio
from agents import Runner
from backend.training_engine import training_writer_agent
from backend.plan_parser import parse_markdown_to_training_material
from collections import defaultdict

# ==========================================
# 📝 EVALUATION TOPICS
# ==========================================
EVALUATION_TOPICS = [
    # === Computer Science & Software Engineering ===
    # Algorithms & Data Structures
    {"name": "Big O Notation", "description": "Understanding how to analyze the performance of algorithms."},
    {"name": "Sorting Algorithms", "description": "Comparison of common sorting algorithms like Quicksort, Mergesort, and Heapsort."},
    {"name": "Graph Traversal (BFS, DFS)", "description": "Methods for exploring a graph, visiting all its nodes and edges."},
    {"name": "Dynamic Programming", "description": "A method for solving complex problems by breaking them down into simpler subproblems."},
    {"name": "Hash Tables", "description": "How hash tables work, collision resolution, and their time complexity."},
    # System Design & Architecture
    {"name": "REST APIs", "description": "What are REST APIs and how do they work? Principles and best practices."},
    {"name": "Load Balancing", "description": "Strategies for distributing network or application traffic across multiple servers."},
    {"name": "Database Sharding", "description": "Techniques for horizontally partitioning a database."},
    {"name": "Caching Strategies", "description": "Overview of caching techniques like write-through, write-back, and read-through."},
    # Databases
    {"name": "SQL Joins", "description": "How to combine rows from two or more tables in a relational database."},
    {"name": "Database Indexing", "description": "How indexes work and how they improve query performance."},
    {"name": "NoSQL Databases", "description": "Comparison of different NoSQL database types (Key-Value, Document, Column-family, Graph)."},
    # Networking
    {"name": "TCP/IP Model", "description": "The layers of the TCP/IP protocol suite."},
    {"name": "HTTP/HTTPS", "description": "The difference between HTTP and HTTPS and the basics of TLS/SSL."},
    # Software Engineering Practices
    {"name": "Git Basics", "description": "Common Git commands and branching strategies."},
    {"name": "Unit Testing", "description": "The importance of unit tests and how to write them."},
    {"name": "CI/CD Pipelines", "description": "Continuous Integration and Continuous Deployment concepts."},

    # === Business & Finance ===
    {"name": "Discounted Cash Flow (DCF) Analysis", "description": "A method of valuing a project or company using the time value of money."},
    {"name": "SWOT Analysis", "description": "A framework for identifying Strengths, Weaknesses, Opportunities, and Threats."},
    {"name": "Return on Investment (ROI)", "description": "A performance measure used to evaluate the efficiency of an investment."},
    {"name": "Financial Statements Analysis", "description": "How to read and interpret balance sheets, income statements, and cash flow statements."},
    {"name": "Supply and Demand Economics", "description": "The fundamental economic principle of the relationship between quantity and price."},

    # === Marketing & Sales ===
    {"name": "Digital Marketing Funnel", "description": "The stages a customer goes through from awareness to purchase (e.g., AIDA model)."},
    {"name": "Search Engine Optimization (SEO)", "description": "Techniques to increase website visibility on search engines."},
    {"name": "Content Marketing Strategy", "description": "Creating and distributing valuable content to attract a target audience."},
    {"name": "SPIN Selling Technique", "description": "A sales technique focusing on Situation, Problem, Implication, and Need-payoff questions."},
    {"name": "Customer Relationship Management (CRM)", "description": "Strategies and technologies for managing all your company’s relationships and interactions with customers."},

    # === Healthcare & Life Sciences ===
    {"name": "HIPAA Compliance", "description": "Understanding the rules and regulations for protecting sensitive patient health information."},
    {"name": "Clinical Trial Phases", "description": "The stages of research that a drug or medical device goes through before being approved."},
    {"name": "Evidence-Based Practice", "description": "An approach in healthcare that emphasizes the use of evidence from well-designed research."},
    {"name": "Telemedicine", "description": "The delivery of health care services, where distance is a critical factor."},

    # === Human Resources ===
    {"name": "Behavioral Interview Questions (STAR method)", "description": "A structured manner of responding to behavioral interview questions by discussing a Situation, Task, Action, and Result."},
    {"name": "Employee Onboarding", "description": "The process of integrating a new employee into an organization."},
    {"name": "Performance Management", "description": "The ongoing process of communication between a supervisor and an employee."},
    {"name": "Diversity and Inclusion in the Workplace", "description": "Policies and programs that encourage representation and participation of diverse groups of people."},

    # === Legal & Consulting ===
    {"name": "Contract Law Basics", "description": "Fundamental principles of legally enforceable agreements."},
    {"name": "Intellectual Property (IP)", "description": "Types of IP (patents, trademarks, copyrights) and their importance."},
    {"name": "BCG Matrix", "description": "A portfolio management framework for categorizing a company's business units or products."},
    {"name": "Porter's Five Forces", "description": "A model that identifies and analyzes five competitive forces that shape every industry."}
]


# ==========================================
# 📊 EVALUATION SCRIPT
# ==========================================

async def run_evaluation():
    """
    Runs the training agent for a list of topics and prompts the user for feedback.
    """
    evaluation_results = []

    print("Starting evaluation of the Training Agent...")
    print(f"Found {len(EVALUATION_TOPICS)} topics to evaluate.")
    print("="*40)

    for i, topic in enumerate(EVALUATION_TOPICS):
        print(f"🔄 Processing Topic {i+1}/{len(EVALUATION_TOPICS)}: {topic['name']}...")

        try:
            # 1. Run the agent using the Runner
            prompt = training_writer_agent.instructions.format(task_name=topic["name"], task_desc=topic["description"])
            result = await Runner.run(training_writer_agent, prompt)
            raw_output = result.final_output

            # 2. Parse the output
            parsed_output = parse_markdown_to_training_material(raw_output)
            
            # Add user's time estimate to each resource
            for resource in parsed_output.resources:
                print(f"  - Agent provided: {resource.url} (Agent's est: {resource.estimated_reading_time_minutes} mins)")
                user_time_str = input("    Your estimated time (in minutes) for this resource: ")
                resource.user_estimated_time_minutes = int(user_time_str) if user_time_str.isdigit() else 0


            # 3. Present for evaluation
            print("\n" + "="*40)
            print(f"📖 TOPIC: {topic['name']}")
            print("="*40)
            print("🧠 Explanation:")
            print(parsed_output.explanation)
            
            print("\n" + "-"*40)
            print("✍️ Please evaluate the quality of the generated material:")
            
            # 4. Get user feedback
            quality_rating = input("Rate the overall quality of the explanation and resources (1-5, 5 being best): ")
            usefulness_rating = input("Rate the usefulness for interview prep (1-5, 5 being best): ")
            comments = input("Any additional comments? (Press Enter to skip): ")

            result_entry = {
                "topic": topic["name"],
                "explanation": parsed_output.explanation,
                "resources": [r.dict() for r in parsed_output.resources],
                "quality_rating": int(quality_rating),
                "usefulness_rating": int(usefulness_rating),
                "comments": comments
            }
            evaluation_results.append(result_entry)

        except Exception as e:
            print(f"❌ An error occurred while processing '{topic['name']}': {e}")
            print("Skipping this topic.")

        print("\n" + "="*40 + "\n")

    # 5. Save and summarize results
    if evaluation_results:
        output_filename = "training_evaluation_results.json"
        with open(output_filename, "w") as f:
            json.dump(evaluation_results, f, indent=2)
        print(f"✅ Evaluation complete. Results saved to {output_filename}")
        
        summarize_results(evaluation_results)
    else:
        print("No topics were evaluated.")

def summarize_results(results):
    """Calculates and prints a detailed statistical summary."""
    print("\n" + "="*50)
    print("📊 EVALUATION REPORT")
    print("="*50)

    num_results = len(results)
    
    # --- Overall Averages ---
    avg_quality = sum(r['quality_rating'] for r in results) / num_results
    avg_usefulness = sum(r['usefulness_rating'] for r in results) / num_results
    print("\n--- 📈 Overall Scores ---")
    print(f"Average Quality Score:   {avg_quality:.2f} / 5")
    print(f"Average Usefulness Score: {avg_usefulness:.2f} / 5")

    # --- Time Estimation Analysis ---
    time_diffs = []
    for r in results:
        for resource in r.get("resources", []):
            agent_time = resource.get("estimated_reading_time_minutes", 0)
            user_time = resource.get("user_estimated_time_minutes", 0)
            if agent_time > 0 and user_time > 0:
                time_diffs.append(abs(agent_time - user_time))
    
    if time_diffs:
        avg_time_diff = sum(time_diffs) / len(time_diffs)
        print("\n--- ⏱️ Reading Time Estimation ---")
        print(f"Average absolute difference between Agent and User estimates: {avg_time_diff:.2f} minutes")

    # --- Rating Distributions ---
    quality_dist = defaultdict(int)
    usefulness_dist = defaultdict(int)
    for r in results:
        quality_dist[r['quality_rating']] += 1
        usefulness_dist[r['usefulness_rating']] += 1
        
    print("\n--- 📊 Rating Distributions ---")
    print("Quality Ratings:")
    for rating in sorted(quality_dist.keys()):
        count = quality_dist[rating]
        print(f"  - {rating}/5: {count} times ({count/num_results:.1%})")
        
    print("\nUsefulness Ratings:")
    for rating in sorted(usefulness_dist.keys()):
        count = usefulness_dist[rating]
        print(f"  - {rating}/5: {count} times ({count/num_results:.1%})")
        
    # --- Per-Topic Summary ---
    print("\n--- 📝 Per-Topic Scores (Quality/Usefulness) ---")
    for r in sorted(results, key=lambda x: x['topic']):
        print(f"- {r['topic']:<40} {r['quality_rating']}/5 | {r['usefulness_rating']}/5")
        
    print("\n" + "="*50)


if __name__ == "__main__":
    asyncio.run(run_evaluation())
