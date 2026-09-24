---
title: 'Robot Framework: Generic Test Automation Framework'
library_name: robotframework
pypi_package: robotframework
category: testing
python_compatibility: 3.8+
last_updated: '2025-11-02'
official_docs: https://robotframework.org
official_repository: https://github.com/robotframework/robotframework
maintenance_status: active
---

# Robot Framework

## Core Purpose

Robot Framework is a generic open source automation framework designed for acceptance testing, acceptance test driven development (ATDD), behavior driven development (BDD), and robotic process automation (RPA). It uses a keyword-driven testing approach that enables writing tests in a human-readable, tabular format.

**What problem does it solve?**

- Enables non-programmers to write and maintain automated tests
- Bridges communication gap between technical and non-technical stakeholders
- Provides a unified framework for acceptance testing across different technologies (web, API, desktop, mobile)
- Allows test automation without deep programming knowledge
- Facilitates living documentation through readable test cases

**What would be "reinventing the wheel" without it?**

Without Robot Framework, teams would need to:

- Build custom test execution frameworks with reporting capabilities
- Create their own keyword abstraction layers for business-readable tests
- Develop logging and debugging infrastructure from scratch
- Implement test data parsing for multiple formats (plain text, HTML, reStructuredText)
- Create plugin systems for extending test capabilities
- Build result aggregation and reporting tools

@Source: <https://github.com/robotframework/robotframework/blob/master/README.rst>

## Python Version Compatibility

**Minimum Python version:** 3.8

**Python 3.11-3.14 compatibility status:**

- Python 3.8-3.13: Fully supported (verified in SeleniumLibrary)
- Python 3.14: Expected to work (no known blockers)

**Version differences:**

- Robot Framework 7.x (current): Requires Python 3.8+
- Robot Framework 6.1.1: Last version supporting Python 3.6-3.7
- Robot Framework 4.1.3: Last version supporting Python 2.7, Jython, IronPython

@Source: <https://github.com/robotframework/robotframework/blob/master/INSTALL.rst> @Source: <https://github.com/robotframework/SeleniumLibrary/blob/master/README.rst>

## Installation

```bash
# Install latest stable version
pip install robotframework

# Install specific version
pip install robotframework==7.3.2

# Upgrade to latest
pip install --upgrade robotframework

# Install with common libraries
pip install robotframework robotframework-seleniumlibrary robotframework-requests
```

@Source: <https://github.com/robotframework/robotframework/blob/master/INSTALL.rst>

## When to Use Robot Framework

**Use Robot Framework when:**

1. **Acceptance testing is the primary goal**

   - You need stakeholder-readable test cases
   - Business analysts or QA engineers write tests without coding
   - Tests serve as living documentation

2. **Keyword-driven testing fits your workflow**

   - You want to build reusable test components (keywords)
   - Test cases follow similar patterns with different data
   - Abstraction layers improve maintainability

3. **Cross-technology testing is required**

   - Testing web applications (via SeleniumLibrary or Browser library)
   - API testing (via RequestsLibrary)
   - Desktop applications (via various libraries)
   - Mobile apps (via AppiumLibrary)
   - SSH/remote systems (via SSHLibrary)

4. **Non-programmers need to contribute to tests**

   - QA teams without Python expertise
   - Domain experts need to validate test logic
   - Collaboration between technical and business teams

5. **RPA (Robotic Process Automation) tasks**
   - Automating repetitive business processes
   - Desktop automation workflows
   - Data migration and validation

**Do NOT use Robot Framework when:**

1. **Unit testing is the primary need**

   - Use pytest for Python unit tests
   - Robot Framework is too heavy for granular testing
   - Fast feedback loops are critical (TDD cycles)

2. **Python-centric test suites**

   - Team consists entirely of Python developers
   - Complex test logic requires extensive Python code
   - pytest fixtures and parametrization are more natural

3. **Performance testing**

   - Use locust, JMeter, or k6 instead
   - Robot Framework adds overhead for load testing

4. **Rapid TDD cycles**

   - Robot Framework startup time is slower than pytest
   - Test discovery and execution have overhead
   - pytest is better for red-green-refactor cycles

5. **Complex test orchestration**
   - Use pytest with advanced fixtures
   - Dependency injection patterns work better in pure Python

@Source: Based on framework design patterns and ecosystem analysis

## Decision Matrix

| Requirement            | Robot Framework | pytest | Recommendation                                     |
| ---------------------- | --------------- | ------ | -------------------------------------------------- |
| Acceptance testing     | ★★★★★           | ★★☆☆☆  | Robot Framework                                    |
| Unit testing           | ★☆☆☆☆           | ★★★★★  | pytest                                             |
| API testing            | ★★★★☆           | ★★★★☆  | Either (RF for acceptance, pytest for integration) |
| Web UI testing         | ★★★★★           | ★★★☆☆  | Robot Framework                                    |
| Non-programmer writers | ★★★★★           | ★☆☆☆☆  | Robot Framework                                    |
| TDD cycles             | ★★☆☆☆           | ★★★★★  | pytest                                             |
| Living documentation   | ★★★★★           | ★★☆☆☆  | Robot Framework                                    |
| Python developers only | ★★☆☆☆           | ★★★★★  | pytest                                             |
| BDD/Gherkin style      | ★★★★☆           | ★★★★☆  | Either (RF native, pytest with behave)             |
| RPA/automation         | ★★★★★           | ★★☆☆☆  | Robot Framework                                    |

## Core Concepts

### Keyword-Driven Testing Approach

Robot Framework tests are built from keywords - reusable test steps that can be combined to create test cases. Keywords can be:

- Built-in keywords from Robot Framework core
- Library keywords from external libraries (SeleniumLibrary, RequestsLibrary, etc.)
- User-defined keywords created in test files or resource files

### Test Case Syntax

```robotframework
*** Settings ***
Documentation     Example test suite showing Robot Framework syntax
Library           SeleniumLibrary
Library           RequestsLibrary
Resource          common_keywords.resource

*** Variables ***
${LOGIN_URL}      http://localhost:8080/login
${BROWSER}        Chrome
${API_URL}        http://localhost:8080/api

*** Test Cases ***
Valid User Login
    [Documentation]    Test successful login with valid credentials
    [Tags]    smoke    login
    Open Browser To Login Page
    Input Username    demo
    Input Password    mode
    Submit Credentials
    Welcome Page Should Be Open
    [Teardown]    Close Browser

API Health Check
    [Documentation]    Verify API is responding
    ${response}=    GET    ${API_URL}/health
    Status Should Be    200
    Should Be Equal As Strings    ${response.json()}[status]    healthy

*** Keywords ***
Open Browser To Login Page
    Open Browser    ${LOGIN_URL}    ${BROWSER}
    Title Should Be    Login Page

Input Username
    [Arguments]    ${username}
    Input Text    username_field    ${username}

Input Password
    [Arguments]    ${password}
    Input Text    password_field    ${password}

Submit Credentials
    Click Button    login_button

Welcome Page Should Be Open
    Title Should Be    Welcome Page
```

@Source: <https://github.com/robotframework/SeleniumLibrary/blob/master/README.rst> @Source: <https://github.com/robotframework/robotframework> (User Guide examples)

## Real-World Usage Patterns

### Pattern 1: Web Testing with SeleniumLibrary

SeleniumLibrary is the most popular Robot Framework library for web testing, supporting Selenium 4 and Python 3.8-3.13.

```robotframework
*** Settings ***
Library           SeleniumLibrary

*** Test Cases ***
Search Product
    Open Browser    https://example.com    Chrome
    Input Text    id:search-input    laptop
    Click Button    id:search-button
    Page Should Contain    Search Results
    Close Browser
```

**Example repositories:**

- <https://github.com/robotframework/SeleniumLibrary> (1,450+ stars)
- <https://github.com/robotframework/WebDemo> (demo project)

@Source: <https://github.com/robotframework/SeleniumLibrary>

### Pattern 2: Modern Browser Testing with Browser Library

Browser library (powered by Playwright) is the next-generation web testing library, offering better performance and reliability.

```robotframework
*** Settings ***
Library           Browser

*** Test Cases ***
Fast Modern Web Test
    New Browser    chromium    headless=False
    New Page       https://example.com
    Type Text      id=search    robot framework
    Click          button#submit
    Get Text       h1    ==    Results
    Close Browser
```

**Example repository:**

- <https://github.com/MarketSquare/robotframework-browser> (605+ stars)

@Source: <https://github.com/MarketSquare/robotframework-browser>

### Pattern 3: API Testing with RequestsLibrary

RequestsLibrary wraps the Python requests library for API testing.

```robotframework
*** Settings ***
Library           RequestsLibrary

*** Test Cases ***
GET Request Test
    ${response}=    GET    https://jsonplaceholder.typicode.com/posts/1
    Should Be Equal As Strings    1    ${response.json()}[id]
    Status Should Be    200

POST Request Test
    &{data}=    Create Dictionary    title=Test    body=Content    userId=1
    ${response}=    POST    https://jsonplaceholder.typicode.com/posts
    ...    json=${data}
    Status Should Be    201
```

**Example repository:**

- <https://github.com/MarketSquare/robotframework-requests> (506+ stars)

@Source: <https://github.com/MarketSquare/robotframework-requests/blob/master/README.md>

### Pattern 4: Data-Driven Testing

The data-driven approach excels when the same workflow needs to be executed with different inputs.

```robotframework
*** Settings ***
Test Template     Calculate

*** Test Cases ***    Expression    Expected
Addition              12 + 2 + 2    16
                      2 + -3        -1
Subtraction           12 - 2 - 2    8
                      2 - -3        5
Multiplication        12 * 2 * 2    48
Division              12 / 2 / 2    3

*** Keywords ***
Calculate
    [Arguments]    ${expression}    ${expected}
    ${result}=    Evaluate    ${expression}
    Should Be Equal As Numbers    ${result}    ${expected}
```

@Source: <https://github.com/robotframework/RobotDemo/blob/master/data_driven.robot>

### Pattern 5: BDD/Gherkin Style

Robot Framework supports Given-When-Then syntax for behavior-driven development.

```robotframework
*** Test Cases ***
User Can Purchase Product
    Given user is logged in
    When user adds product to cart
    And user proceeds to checkout
    Then order should be confirmed

*** Keywords ***
User Is Logged In
    Open Browser To Login Page
    Login With Valid Credentials

User Adds Product To Cart
    Search For Product    laptop
    Add First Result To Cart

User Proceeds To Checkout
    Click Cart Icon
    Click Checkout Button

Order Should Be Confirmed
    Page Should Contain    Order Confirmed
```

@Source: Robot Framework User Guide (Gherkin style examples)

## Integration Patterns

### SeleniumLibrary (Web Testing)

```bash
pip install robotframework-seleniumlibrary
```

- Most mature web testing library
- Supports Selenium 4
- Selenium Manager handles browser drivers automatically
- Python 3.8-3.13 compatible

@Source: <https://github.com/robotframework/SeleniumLibrary>

### Browser Library (Modern Web Testing)

```bash
pip install robotframework-browser
rfbrowser init  # Install Playwright browsers
```

- Powered by Playwright
- Better performance and reliability than Selenium
- Built-in waiting and auto-retry mechanisms
- Supports modern browser features

@Source: <https://github.com/MarketSquare/robotframework-browser>

### RequestsLibrary (API Testing)

```bash
pip install robotframework-requests
```

- Wraps Python requests library
- RESTful API testing
- OAuth and authentication support
- JSON/XML response validation

@Source: <https://github.com/MarketSquare/robotframework-requests>

### SSHLibrary (Remote Testing)

```bash
pip install robotframework-sshlibrary
```

- SSH and SFTP operations
- Remote command execution
- File transfer capabilities
- Terminal emulation

@Source: <https://github.com/MarketSquare/SSHLibrary>

### AppiumLibrary (Mobile Testing)

```bash
pip install robotframework-appiumlibrary
```

- Mobile app testing (iOS/Android)
- Built on Appium
- Cross-platform mobile automation

@Source: <https://github.com/serhatbolsu/robotframework-appiumlibrary>

## Custom Keyword Libraries

Robot Framework can be extended with Python libraries:

```python
# MyLibrary.py
class MyLibrary:
    """Custom keyword library for Robot Framework."""

    def __init__(self, host, port=80):
        """Library initialization with arguments."""
        self.host = host
        self.port = port

    def connect_to_service(self):
        """Keyword: Connect To Service

        Establishes connection to the configured service.
        """
        # Implementation
        pass

    def send_message(self, message):
        """Keyword: Send Message

        Sends a message to the service.

        Arguments:
            message: The message to send
        """
        # Implementation
        pass
```

Usage in test:

```robotframework
*** Settings ***
Library    MyLibrary    localhost    8080

*** Test Cases ***
Send Test Message
    Connect To Service
    Send Message    Hello, Robot Framework!
```

@Source: <https://github.com/robotframework/robotframework> (User Guide - Creating Libraries)

## Execution and Reporting

### Basic Execution

```bash
# Run all tests in a file
robot tests.robot

# Run tests in a directory
robot path/to/tests/

# Run with specific browser
robot --variable BROWSER:Firefox tests.robot

# Run tests with specific tags
robot --include smoke tests/

# Run and generate custom output directory
robot --outputdir results tests.robot

# Run with Python module syntax
python -m robot tests.robot
```

### Advanced Execution

```bash
# Parallel execution (with pabot)
pip install robotframework-pabot
pabot --processes 4 tests/

# Re-run failed tests
robot --rerunfailed output.xml tests.robot

# Combine multiple test results
rebot --name Combined output1.xml output2.xml
```

@Source: <https://github.com/robotframework/robotframework/blob/master/doc/userguide/src/ExecutingTestCases/BasicUsage.rst>

## Ecosystem Tools

### RIDE (Test Editor)

Desktop IDE for creating and editing Robot Framework tests. Supports Python 3.8-3.13.

```bash
pip install robotframework-ride
ride.py
```

@Source: <https://github.com/robotframework/RIDE>

### RobotCode (VS Code Extension)

LSP-powered VS Code extension for Robot Framework development.

- Syntax highlighting and code completion
- Debugging support
- Test execution from IDE
- Keyword documentation

@Source: <https://github.com/robotcodedev/robotcode>

### Robocop (Linter)

Static code analysis and linting tool for Robot Framework.

```bash
pip install robotframework-robocop
robocop tests/
```

@Source: <https://github.com/MarketSquare/robotframework-robocop>

### Tidy (Code Formatter)

Code formatting tool for Robot Framework files.

```bash
pip install robotframework-tidy
robotidy tests/
```

@Source: <https://github.com/MarketSquare/robotframework-tidy> (referenced in ecosystem)

## Maintenance Status

**Status:** Actively maintained

- Latest stable: 7.3.2 (July 2025)
- Latest pre-release: 7.4b1 (October 2025)
- Active development on GitHub (11,000+ stars, 2,400+ forks)
- Non-profit Robot Framework Foundation provides governance
- Regular releases (multiple per year)
- Strong community support (Slack, Forum, GitHub)

**Project Health Indicators:**

- 269 open issues (October 2025)
- Active commit history
- Responsive maintainers
- Large ecosystem of maintained libraries
- Corporate backing and foundation support

@Source: <https://github.com/robotframework/robotframework> @Source: <https://pypi.org/project/robotframework/>

## Comparison with Alternatives

### vs pytest

**Choose Robot Framework:**

- Acceptance testing focus
- Non-programmers write tests
- Keyword-driven approach preferred
- Cross-technology testing (web, API, desktop, mobile)
- Living documentation requirement

**Choose pytest:**

- Unit testing focus
- Python developers only
- Complex test logic in Python
- Rapid TDD cycles
- Python-native fixtures and parametrization

### vs Behave (Python BDD)

**Choose Robot Framework:**

- Broader scope (not just BDD)
- Rich ecosystem of libraries
- Keyword reusability across projects
- Built-in reporting and logging

**Choose Behave:**

- Pure BDD/Gherkin focus
- Step definitions in Python
- Integration with pytest

### vs Cucumber (JVM BDD)

**Choose Robot Framework:**

- Python ecosystem
- RPA capabilities
- Broader than just BDD

**Choose Cucumber:**

- JVM ecosystem (Java, Kotlin, Scala)
- Pure Gherkin syntax
- Enterprise Java integration

## Example Projects

1. **RobotDemo** - Official demo project

   - <https://github.com/robotframework/RobotDemo>
   - Shows keyword-driven, data-driven, and Gherkin styles
   - Calculator library implementation example

2. **WebDemo** - Web testing demo

   - Referenced in SeleniumLibrary docs
   - Complete login test example with page objects

3. **awesome-robotframework** - Curated resources
   - <https://github.com/MarketSquare/awesome-robotframework>
   - Libraries, tools, and example projects
   - Community contributions

@Source: <https://github.com/robotframework/RobotDemo> @Source: <https://github.com/MarketSquare/awesome-robotframework>

## Summary

Robot Framework is the premier choice for acceptance testing and RPA in the Python ecosystem. Its keyword-driven approach enables collaboration between technical and non-technical team members, making it ideal for projects where tests serve as living documentation. The framework excels at cross-technology testing (web, API, mobile, desktop) through its rich ecosystem of libraries.

However, it is not a replacement for pytest in unit testing scenarios. Teams should use Robot Framework for acceptance-level tests and pytest for unit/integration tests. The frameworks complement each other well in a comprehensive testing strategy.

**Quick decision guide:**

- Need stakeholder-readable tests? → Robot Framework
- Need unit tests? → pytest
- Need both? → Use both frameworks together
- Pure Python developers doing integration tests? → Consider pytest first
- QA team without coding experience? → Robot Framework

The framework's active maintenance, strong community, and foundation backing ensure long-term viability for projects adopting it.
