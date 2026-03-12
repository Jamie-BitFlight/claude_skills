# Code Examples

## Testing Functions in Isolation

```bash
#!/usr/bin/env bash

# my_functions.sh
calculate_sum() {
    local -i sum=0
    for num in "$@"; do
        sum+=num
    done
    echo "$sum"
}

validate_email() {
    [[ "${1}" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$ ]]
}
```

## Basic Spec Structure

```bash
# spec/functions_spec.sh

Describe 'calculate_sum'
  Include lib/functions.sh

  It 'returns 0 for no arguments'
    When call calculate_sum
    The output should eq "0"
    The status should be success
  End

  It 'sums multiple numbers'
    When call calculate_sum 1 2 3 4 5
    The output should eq "15"
  End
End

Describe 'validate_email'
  Include lib/functions.sh

  It 'accepts valid email'
    When call validate_email "test@example.com"
    The status should be success
  End

  It 'rejects invalid email'
    When call validate_email "not-an-email"
    The status should be failure
  End

  Parameters
    "user@domain.com"    success
    "user.name@sub.domain.org" success
    "invalid"            failure
    "@nodomain.com"      failure
  End

  Example "validates ${1}"
    When call validate_email "${1}"
    The status should be "${2}"
  End
End
```
