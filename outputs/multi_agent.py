Here's the implementation of `multi_agent.py` based on your instructions:

```python
import argparse
from rtx_agent import RTXAgent

class MultiAgent:
    def __init__(self):
        self.agents = []

    def add_agent(self, agent_name, task):
        if agent_name == 'researcher':
            prompt = 'Research Prompt: '
        elif agent_name == 'coder':
            prompt = 'Code Prompt: '
        else:
            raise ValueError('Invalid agent name')

        self.agents.append(RTXAgent(prompt=prompt, task=task))

    def run_agents(self):
        for i, agent in enumerate(self.agents):
            print(f'Running Agent {i+1}: {agent.name}')
            result = agent.run()
            if i < len(self.agents) - 1:
                self.agents[i + 1].input = result

    def start(self):
        parser = argparse.ArgumentParser(description='Multi-Agent Coordinator')
        parser.add_argument('--task', type=str, required=True)
        parser.add_argument('--agents', type=str, nargs='+', required=True)
        args = parser.parse_args()

        self.add_agent(*args.agents, task=args.task)
        self.run_agents()


if __name__ == '__main__':
    MultiAgent().start()
```

And here's the implementation of `rtx_agent.py`:

```python
class RTXAgent:
    def __init__(self, prompt, task):
        self.name = 'RTX Agent'
        self.prompt = prompt
        self.task = task
        self.input = ''

    def run(self):
        print(f'{self.name} is running...')
        # Simulate agent's work based on the input and task
        if self.input:
            result = f'Agent {self.name} processed: {self.input}'
        else:
            result = f'Agent {self.name} started with prompt: {self.prompt}'
        print(result)
        return result


if __name__ == '__main__':
    RTXAgent('System Prompt: ', 'Task').run()
```

To run the coordinator, use the following command:

```bash
python multi_agent.py --task X --agents researcher,coder
```

This will create a `MultiAgent` object and add two agents (`researcher` and `coder`) to it. The `run_agents` method will then run each agent sequentially, passing the result of the previous agent as input to the next one.