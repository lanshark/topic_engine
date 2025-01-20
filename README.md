# The Topic Engine

The Topic Engine is an open-source distributed content intelligence system that enables autonomous discovery, monitoring, and processing of topic-specific content across the internet. It transforms unstructured web content into structured, actionable intelligence by understanding content patterns, site structures, and topic relevance.

## 🌟 Key Features

- **Intelligent Content Discovery**: Autonomous identification and monitoring of relevant content sources
- **Smart Content Processing**: Advanced content extraction with fallback strategies
- **Topic Classification**: Efficient few-shot learning for content categorization
- **Structured Data Extraction**: Turn unstructured content into actionable data
- **Geographic Context**: Location-aware content processing and analysis
- **Extensible Architecture**: Plugin-based design for easy customization

## 🚀 Vision

The Topic Engine aims to be more than just a content processing system - it's a step towards democratizing content intelligence and enabling personal AI systems. Our goals include:

- Creating an open, collaborative platform for content processing and analysis
- Enabling individuals and small teams to build sophisticated content monitoring systems
- Fostering a community-driven approach to content intelligence
- Supporting the development of personal AI assistants and tools

## 🛠 Technical Overview

The Topic Engine is built with:

- Django for the core framework
- SetFit for few-shot learning and classification
- Playwright for reliable content extraction
- PostgreSQL/PostGIS for data storage
- Modern async architecture for efficient processing

Key components include:

- Content source management and monitoring
- Multi-strategy content fetching system
- Topic hierarchy and classification
- Content processing pipelines
- Geographic context integration

## 🌱 Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL 15+ with PostGIS
- Redis (for caching and async tasks)

### Quick Start

1. Clone the repository:
```bash
git clone https://github.com/NimbleMachine-andrew/topic_engine.git
cd topic_engine
```

2. We use [UV](https://docs.astral.sh/uv/) to Manage dependencies:
```bash
uv venv
uv sync
```

3. Create a .env file.

    Copy the env-example to .env, edit for your values.


4. Create a postgres/postgis database for the application:

    Create a User:

```bash
    sudo -u postgres psql << EOF
        CREATE USER topic_engine WITH PASSWORD 'mypassword';
    EOF
```

```bash
    sudo -u postgres psql << EOF 
        DROP DATABASE IF EXISTS topic_engine;
        CREATE DATABASE topic_engine ENCODING='UTF-8' OWNER topic_engine;
        \c topic_engine
        CREATE EXTENSION postgis;
        CREATE EXTENSION postgis_topology;
        ALTER DATABASE topic_engine OWNER TO topic_engine;
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO topic_engine;
        GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO topic_engine;
        GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO topic_engine;
    EOF
```

5. Set up the database:
```bash
uv run manage.py migrate
```

6. Pre-load the data:
```bash
./manage.py loaddata initial_topics
./manage.py loaddata initial_model_configs
./manage.py train_setfit_model personal_ai_medium
./manage.py predict_topics  (also takes a batch-size parameter:  --batch-size=50)

```

7. Run the development server:
```bash
uv run manage.py runserver
```

## 🤝 Contributing

We welcome contributions of all kinds! Whether you're fixing bugs, adding features, or improving documentation, your help is appreciated.

### Ways to Contribute

1. 🐛 Report bugs and suggest features
2. 📝 Improve documentation
3. 🔧 Submit pull requests
4. 🎨 Help with UI/UX design
5. 🧪 Add tests and improve coverage
6. 🌍 Help with internationalization

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 🤲 Community and Cooperation

The Topic Engine is more than a software project - it's an experiment in cooperative development and community-driven innovation. We're exploring ways to:

- Build a sustainable cooperative business model
- Create opportunities for contributors
- Foster collaboration and knowledge sharing
- Develop ethical approaches to AI and content processing

Join our community:
- [Discord](https://discord.gg/topic-engine) (Coming soon)
- [Matrix Chat](https://matrix.to/#/#topic-engine:matrix.org) (Coming soon)
- [Forum](https://forum.topic-engine.org) (Coming soon)

## 📜 License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0) - see the [LICENSE](LICENSE) file for details.

We chose the AGPL to:
- Ensure the software remains open source
- Protect community contributions
- Support cooperative business models
- Maintain transparency and trust

## 📋 Roadmap

Check our [Project Board](https://github.com/NimbleMachine-andrew/topic_engine/projects/1) for current development priorities.

Near-term goals:
- [ ] Improve documentation and examples
- [ ] Add more content source types
- [ ] Enhance topic classification
- [ ] Implement plugin system
- [ ] Build community tools and resources

## ✨ Acknowledgements

The Topic Engine builds on many excellent open source projects and ideas. Special thanks to:
- The SetFit team for few-shot learning
- Django community
- Playwright developers
- PostGIS contributors

## 🤔 Questions?

Feel free to [open an issue](https://github.com/NimbleMachine-andrew/topic_engine/issues) or join our community channels. We're here to help!
