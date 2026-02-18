Here is the implementation code for PHASE 1:

**qdrant_memory.py**
```python
import qdrant_client as qc
from qdrant_client import VectorMemory

class QdrantMemory:
    def __init__(self, db_path):
        self.db = qc.VectorMemory(db_path)

    def store_task(self, task_id, task_data):
        self.db.add_vector(task_id, task_data)

    def get_task(self, task_id):
        return self.db.get_vector(task_id)
```
**langchain_integration.py**
```python
import langchain as lc
from rtx_agent import RTXAgent

class LangChainIntegration:
    def __init__(self, agent: RTXAgent):
        self.agent = agent
        self.lang_chain = lc.LangChain()

    def integrate(self):
        # Integrate LangChain with RTX Agent
        self.agent.chain_memory = self.lang_chain.memory
        self.agent.task_orchestration = self.lang_chain.orchestrate

    def get_task_results(self, task_id):
        return self.lang_chain.get_task_results(task_id)
```
**rtx_agent.py (updated)**
```python
import qdrant_memory as qm
from langchain_integration import LangChainIntegration

class RTXAgent:
    def __init__(self, db_path):
        self.memory = QdrantMemory(db_path)
        self.lang_chain_integrator = LangChainIntegration(self)

    def store_task(self, task_id, task_data):
        self.memory.store_task(task_id, task_data)

    def get_task_results(self, task_id):
        return self.memory.get_task(task_id) + self.lang_chain_integrator.get_task_results(task_id)
```
**Setup Instructions:**

1. Install Qdrant and LangChain using pip:
```
pip install qdrant-client langchain langchain-community
```
2. Create a persistent memory database for the agent:
```python
qm = qm.QdrantMemory('path/to/memory.db')
rtx_agent.memory = qm
```
3. Integrate LangChain with the RTX Agent:
```python
lc_integrator = LangChainIntegration(rtx_agent)
lc_integrator.integrate()
```
4. Update the RTX Agent to use persistent memory and integrate LangChain:
```python
rtx_agent.store_task(task_id, task_data)
results = rtx_agent.get_task_results(task_id)
print(results)
```
This implementation code for PHASE 1 sets up a vector memory system using Qdrant and integrates LangChain with the RTX Agent. The updated RTX Agent uses persistent memory to store tasks and results, and LangChain is used to orchestrate task execution and store learnings.

Note: This code assumes that you have already implemented the RTX Agent and its dependencies.