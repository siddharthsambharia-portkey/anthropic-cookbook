import sqlite3

def get_schema_info(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    schema_info = []
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    for (table_name,) in tables:
        # Get columns for this table
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        table_info = f"Table: {table_name}\n"
        table_info += "\n".join(f"  - {col[1]} ({col[2]})" for col in columns)
        schema_info.append(table_info)
    
    conn.close()
    return "\n\n".join(schema_info)

def generate_prompt(user_query, db_path='../data/data.db'):
    schema = get_schema_info(db_path)
    return f"""
    You are an AI assistant that converts natural language queries into SQL. 
    Given the following SQL database schema:

    {schema}

    Convert the following natural language query into SQL:

    {user_query}

    Provide only the SQL query in your response, enclosed within <sql> tags.
    """

def generate_prompt_with_examples(user_query, db_path='../data/data.db'):
    examples = """
        Example 1:
        <query>List all employees in the HR department.</<query>
        <output>SELECT e.name FROM employees e JOIN departments d ON e.department_id = d.id WHERE d.name = 'HR';</output>

        Example 2:
        User: What is the average salary of employees in the Engineering department?
        SQL: SELECT AVG(e.salary) FROM employees e JOIN departments d ON e.department_id = d.id WHERE d.name = 'Engineering';

        Example 3:
        User: Who is the oldest employee?
        SQL: SELECT name, age FROM employees ORDER BY age DESC LIMIT 1;
    """

    schema = get_schema_info(db_path)

    return f"""
        You are an AI assistant that converts natural language queries into SQL.
        Given the following SQL database schema:

        <schema>
        {schema}
        </schema>

        Here are some examples of natural language queries and their corresponding SQL:

        <examples>
        {examples}
        </examples>

        Now, convert the following natural language query into SQL:
        <query>
        {user_query}
        </query>

        Provide only the SQL query in your response, enclosed within <sql> tags.
    """

def generate_prompt_with_cot(user_query, db_path='../data/data.db'):
    schema = get_schema_info(db_path)
    examples = """
    <example>
    <query>List all employees in the HR department.</query>
    <thought_process>
    1. We need to join the employees and departments tables.
    2. We'll match employees.department_id with departments.id.
    3. We'll filter for the HR department.
    4. We only need to return the employee names.
    </thought_process>
    <sql>SELECT e.name FROM employees e JOIN departments d ON e.department_id = d.id WHERE d.name = 'HR';</sql>
    </example>
    """
    return f"""
    You are an AI assistant that converts natural language queries into SQL.
    Given the following SQL database schema:

    {schema}

    Here are some examples of natural language queries, thought processes, and corresponding SQL queries:

    {examples}

    Now, convert the following natural language query into SQL:
    {user_query}

    First, provide your thought process within <thought_process> tags, explaining how you'll approach creating the SQL query.
    Then, provide the SQL query within <sql> tags.
    """

def generate_prompt_with_rag(user_query, db_path='../data/data.db'):
    from vectordb import VectorDB
    
    # Load the vector database
    vectordb = VectorDB()
    vectordb.load_db()

    if not vectordb.embeddings:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            schema_data = [
                {"text": f"Table: {table[0]}, Column: {col[1]}, Type: {col[2]}", 
                "metadata": {"table": table[0], "column": col[1], "type": col[2]}}
                for table in cursor.fetchall()
                for col in cursor.execute(f"PRAGMA table_info({table[0]})").fetchall()
            ]
        vectordb.load_data(schema_data)

    relevant_schema = vectordb.search(user_query, k=10, similarity_threshold=0.3)
    schema_info = "\n".join([f"Table: {item['metadata']['table']}, Column: {item['metadata']['column']}, Type: {item['metadata']['type']}"
                             for item in relevant_schema])
    return f"""
    You are an AI assistant that converts natural language queries into SQL.
    Given the following relevant columns from the SQL database schema:

    {schema_info}

    Convert the following natural language query into SQL:

    {user_query}

    First, provide your thought process within <thought_process> tags, explaining how you'll approach creating the SQL query.
    Then, provide the SQL query within <sql> tags.

    Ensure your SQL query is compatible with SQLite syntax.
    """