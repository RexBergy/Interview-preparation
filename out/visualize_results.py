import json
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def load_data(results_path="training_evaluation_results.json"):
    """Loads and preprocesses the evaluation results from the JSON file."""
    if not os.path.exists(results_path):
        print(f"Error: {results_path} not found.")
        return None

    with open(results_path, "r") as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    df['average_rating'] = df[['quality_rating', 'usefulness_rating']].mean(axis=1)
    return df

def plot_ratings_per_topic(df, output_dir):
    """Generates a sorted horizontal bar chart for ratings per topic using seaborn."""
    df_sorted = df.sort_values('average_rating', ascending=False)
    
    plt.figure(figsize=(12, 10))
    # Melting the dataframe to have a single column for ratings and a column for rating_type
    df_melted = df_sorted.melt(id_vars=['topic'], value_vars=['quality_rating', 'usefulness_rating'],
                               var_name='rating_type', value_name='rating')

    sns.barplot(data=df_melted, y='topic', x='rating', hue='rating_type', palette='viridis')
    
    plt.title('Quality and Usefulness Ratings per Topic', fontsize=16)
    plt.xlabel('Rating (1-5)', fontsize=12)
    plt.ylabel('Topic', fontsize=12)
    plt.legend(title='Rating Type')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "ratings_per_topic.png"))
    plt.close()
    print("✅ Generated ratings_per_topic.png")

def plot_ratings_distribution(df, output_dir):
    """Generates count plots for the distribution of ratings using seaborn."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    sns.countplot(ax=ax1, data=df, x='quality_rating', palette='Blues')
    ax1.set_title('Quality Rating Distribution', fontsize=14)
    ax1.set_xlabel('Rating', fontsize=12)
    ax1.set_ylabel('Frequency', fontsize=12)

    sns.countplot(ax=ax2, data=df, x='usefulness_rating', palette='Greens')
    ax2.set_title('Usefulness Rating Distribution', fontsize=14)
    ax2.set_ylabel('Frequency', fontsize=12)
    ax2.set_xlabel('Rating', fontsize=12)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "ratings_distribution.png"))
    plt.close()
    print("✅ Generated ratings_distribution.png")

def plot_time_estimation_comparison(df, output_dir):
    """
    Generates a box plot of the percentage error in agent time estimation,
    binned by user-estimated reading time.
    """
    resources_data = []
    for _, row in df.iterrows():
        for resource in row['resources']:
            agent_time = resource.get('estimated_reading_time_minutes', 0)
            user_time = resource.get('user_estimated_time_minutes', 0)
            if user_time > 0:  # Avoid division by zero
                percentage_error = ((agent_time - user_time) / user_time) * 100
                resources_data.append({
                    'user_time': user_time,
                    'percentage_error': percentage_error
                })

    if not resources_data:
        print("ℹ️ No resource time data to plot.")
        return

    resources_df = pd.DataFrame(resources_data)

    # Create bins for user-estimated time
    bins = [0, 5, 10, 20, 30, 60, np.inf]
    labels = ['0-5', '5-10', '10-20', '20-30', '30-60', '60+']
    resources_df['time_bin'] = pd.cut(resources_df['user_time'], bins=bins, labels=labels, right=False)

    plt.figure(figsize=(14, 8))
    sns.boxplot(data=resources_df, x='time_bin', y='percentage_error', palette='coolwarm')

    plt.title('Agent Time Estimation Error by Article Length', fontsize=16)
    plt.xlabel('User Estimated Reading Time (minutes)', fontsize=12)
    plt.ylabel('Estimation Error (%)', fontsize=12)
    plt.axhline(0, color='black', linestyle='--', label='Ideal Estimation (0% Error)')
    
    # Setting a more reasonable y-axis limit if there are extreme outliers
    # For example, limit to the 98th percentile of the absolute error
    max_error = resources_df['percentage_error'].abs().quantile(0.98)
    if not np.isnan(max_error) and max_error > 0:
        plt.ylim(-max_error, max_error)

    plt.legend()
    plt.grid(axis='y')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "time_estimation_comparison_binned.png"))
    plt.close()
    print("✅ Generated time_estimation_comparison_binned.png")

def plot_time_estimation_comparison_scatter(df, output_dir):
    """
    Generates a scatter plot of Agent Estimated Time vs. User Estimated Time
    for a direct visual comparison.
    """
    resources_data = []
    for _, row in df.iterrows():
        for resource in row['resources']:
            agent_time = resource.get('estimated_reading_time_minutes', 0)
            user_time = resource.get('user_estimated_time_minutes', 0)
            if user_time > 0:  # Include if user time is provided
                resources_data.append({
                    'agent_time': agent_time,
                    'user_time': user_time,
                    'topic': row['topic']
                })

    if not resources_data:
        print("ℹ️ No resource time data for scatter plot.")
        return

    resources_df = pd.DataFrame(resources_data)

    plt.figure(figsize=(10, 10))
    sns.scatterplot(data=resources_df, x='user_time', y='agent_time', hue='topic', alpha=0.7, s=100)
    
    # Add a y=x line for perfect agreement
    max_val = max(resources_df['user_time'].max(), resources_df['agent_time'].max())
    plt.plot([0, max_val], [0, max_val], color='red', linestyle='--', label='Perfect Agreement')

    plt.title('Agent vs. User Time Estimation', fontsize=16)
    plt.xlabel('User Estimated Reading Time (minutes)', fontsize=12)
    plt.ylabel('Agent Estimated Reading Time (minutes)', fontsize=12)
    plt.legend(title='Topic', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "time_estimation_comparison_scatter.png"))
    plt.close()
    print("✅ Generated time_estimation_comparison_scatter.png")

def plot_time_estimation_comparison_log(df, output_dir):
    """
    Generates a log-log scatter plot of agent vs. user estimated reading times
    to better visualize data across different scales.
    """
    resources_data = []
    for _, row in df.iterrows():
        for resource in row['resources']:
            agent_time = resource.get('estimated_reading_time_minutes', 0)
            user_time = resource.get('user_estimated_time_minutes', 0)
            # We only include data points where both times are positive for log scale
            if agent_time > 0 and user_time > 0:
                resources_data.append({
                    'agent_time': agent_time,
                    'user_time': user_time
                })

    if not resources_data:
        print("ℹ️ No resource time data for log-log plot.")
        return

    resources_df = pd.DataFrame(resources_data)

    plt.figure(figsize=(10, 10))
    sns.scatterplot(data=resources_df, x='user_time', y='agent_time', alpha=0.6)
    
    # Set log scale
    plt.xscale('log')
    plt.yscale('log')

    # Add a y=x line for perfect agreement
    max_val = max(resources_df['user_time'].max(), resources_df['agent_time'].max())
    min_val = min(resources_df['user_time'].min(), resources_df['agent_time'].min())
    plt.plot([min_val, max_val], [min_val, max_val], color='red', linestyle='--', label='Perfect Agreement')

    plt.title('Agent vs. User Time Estimation (Log Scale)', fontsize=16)
    plt.xlabel('User Estimated Reading Time (minutes, log scale)', fontsize=12)
    plt.ylabel('Agent Estimated Reading Time (minutes, log scale)', fontsize=12)
    plt.legend()
    plt.grid(True, which="both", ls="--")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "time_estimation_comparison_log.png"))
    plt.close()
    print("✅ Generated time_estimation_comparison_log.png")




def plot_correlation_heatmap(df, output_dir):

    """Generates a heatmap of correlations between numeric features using seaborn."""
    agg_times = []
    for index, row in df.iterrows():
        if row['resources']:
            agent_avg = np.mean([r.get('estimated_reading_time_minutes', 0) for r in row['resources']])
            user_avg = np.mean([r.get('user_estimated_time_minutes', 0) for r in row['resources']])
            agg_times.append({'topic': row['topic'], 'agent_time_avg': agent_avg, 'user_time_avg': user_avg})
    
    times_df = pd.DataFrame(agg_times)
    merged_df = pd.merge(df, times_df, on='topic')
    
    corr = merged_df[['quality_rating', 'usefulness_rating', 'agent_time_avg', 'user_time_avg']].corr()
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap='coolwarm', vmin=-1, vmax=1)
    plt.title('Correlation Heatmap of Ratings and Time Estimates', fontsize=15)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "correlation_heatmap.png"))
    plt.close()
    print("✅ Generated correlation_heatmap.png")

def analyze_comments(df, output_dir):
    """Analyzes comments and creates a summary report."""
    comments_df = df[df['comments'].str.strip() != ''][['topic', 'comments']]
    
    if comments_df.empty:
        print("ℹ️ No comments to analyze.")
        return

    report_path = os.path.join(output_dir, "../evaluation_insights.txt")
    with open(report_path, "w") as f:
        f.write("Insights from User Comments\n")
        f.write("=" * 30 + "\n\n")

        common_issues = {
            "Page Not Found": comments_df[comments_df['comments'].str.contains("not found|missing", case=False)].shape[0],
            "Too High-Level": comments_df[comments_df['comments'].str.contains("high level", case=False)].shape[0],
            "Incorrect Content": comments_df[comments_df['comments'].str.contains("not correct", case=False)].shape[0],
            "Subscriber Only": comments_df[comments_df['comments'].str.contains("subscriber", case=False)].shape[0],
        }

        f.write("Summary of Common Issues:\n")
        for issue, count in common_issues.items():
            if count > 0:
                f.write(f"- {issue}: {count} instance(s)\n")
        
        f.write("\n" + "=" * 30 + "\n")
        f.write("All Comments:\n")
        for _, row in comments_df.iterrows():
            f.write(f"\n- Topic: {row['topic']}\n")
            f.write(f"  Comment: {row['comments']}\n")
    
    print(f"✅ Generated comment analysis report: {report_path}")

def visualize_results():
    """
    Loads evaluation results from JSON and generates insightful visualizations.
    """
    # Set seaborn style
    sns.set_theme(style="whitegrid")

    output_dir = "out/plots"
    os.makedirs(output_dir, exist_ok=True)

    df = load_data()
    if df is None:
        return

    plot_ratings_per_topic(df, output_dir)
    plot_ratings_distribution(df, output_dir)
    plot_time_estimation_comparison(df, output_dir)
    plot_time_estimation_comparison_log(df, output_dir)
    plot_time_estimation_comparison_scatter(df, output_dir)

    plot_correlation_heatmap(df, output_dir)
    analyze_comments(df, output_dir)
    
    print("\nVisualizations and analysis complete.")
    print(f"All plots saved in: {output_dir}")
    print(f"Comment analysis saved in: {os.path.join(output_dir, '../evaluation_insights.txt')}")


if __name__ == "__main__":
    visualize_results()