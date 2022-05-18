# Quickstart

PyAstroSALT is a small API which serves as a Python wrapper for the API of the [Southern African Large Telescope (SALT)](https://www.salty.ac.za).

## Before you start...

Most of the API endpoints require you to have a SALT account. If you've ever submitted a SALT proposal or logged into the SALT [Web Manager](https://www.salt.ac.za/wm), you have an account already. You can register for an account on the [registration page](https://www.salt.ac.za/wm/Register/).

## Installing PyAstroSALT

PyAstroSALT can be installed in the usual way with pip.

```shell
python -m pip install PyAstroSALT
```

You need Python 3.7 or higher to use the library.

## Setting up the API server

At the time of writing, you need to tell PyAstroSALT where to find the API server. You do this by assigning its URL to the environment variable `PYASTROSALT_API_SERVER`. As an example, assume you have a script `submit.py` using PyAstroSALT, and the API server URL is `https://api.salt.ac.za`. Then on a Unix system, you can set the environment variable and launch the script by running:

```shell
PYASTROSALT_API_SERVER="https://api.salt.ac.za" python submit.py
```

```{note}
This step will not be required any longer in a future version of PyAstroSALT.
```

## Using PyAstroSALT

We demonstrate the usage of PyAstroSALT by walking through an example script:

```{literalinclude} ../docs_src/quickstart/resubmission.py
---
language: python
---
```

Our general game plan is as follows:

1. "Log in" to the API.
2. Download a proposal as a zip file.
3. Update the proposal content.
4. Resubmit the updated proposal.
5. Watch the progress of the proposal submission.

This is reflected by the main function.

```{literalinclude} ../docs_src/quickstart/resubmission.py
---
language: python
lines: 72-82
emphasize-lines: 4, 6-9
---
```

As you can see, the `main` function is an async function. See the RealPython article on [Async IO in Python](https://realpython.com/async-io-python/) for an in-depth explanation of what this means. One consequence is that the function must be run in an event loop.

```{literalinclude} ../docs_src/quickstart/resubmission.py
---
language: python
lines: 85-86
emphasize-lines: 2
---
```

In the following sections we discuss the various steps of our game plan in more detail.

### Logging in

Most of the SALT API endpoints require the user to be authenticated. PyAstroSALT therefore provides a method for logging in.

```{literalinclude} ../docs_src/quickstart/resubmission.py
---
language: python
lines: 12-16
emphasize-lines: 5
---
```

Technically, the `login` functions requests an authentication token from the server, which is passed along with any future requests. The important thing to bear in mind is that this token has a finite lifetime (of a week); so if you are planning to run a script for days, you'll have to logout and login again every once ion a while.

### Downloading a proposal

Every SALT proposal is uniquely identified by its proposal code, which is an identifier consisting of a year, semester, proposal type and running number. The example code is using the (fictitious) proposal code `2022-1-SCI-042`.

The whole proposal content can be downloaded as a zip file using the `download_zip` function.

```{literalinclude} ../docs_src/quickstart/resubmission.py
---
language: python
lines: 72-82
emphasize-lines: 6
---
```

As we want to modify proposal content, we download it into memory. However, the `download_zip` alternatively accepts a file path, in which case the content is saved in a file, which you can import into SALT's [Principal Investigator Proposal Tool](https://astronomers.salt.ac.za/software/pipt/). If the file exists alrerady, it will be overwritten.

### Tweaking the proposal content

```{warning}
While PyAstroSALT can be used with Python 3.7, the code for parsing the proposal XML only works with Python 3.8 or higher.
```

Amongst others, the downloaded proposal zip file contains an XML file, `Proposal.xml`, with the proposal content. This contains _blocks_, which in SALT terms are the minimum schedulable units in a proposal. Our aim is twofold:

1. Update the block name, adding " (v2)" to it.
2. Replace the block code with a new one. This effectively turns this block into a completely new one.

The code for accomplishing this does not use PyAstroSALT. It essentially decompresses the zip file, extracts the XML describing the proposal, modifies the XML saves the updated XML and all the other files in a new zip file.

```{literalinclude} ../docs_src/quickstart/resubmission.py
---
language: python
lines: 19-57
---
```

More details on parsing and modifying XML can be found in the [ElementTree tutorial](https://docs.python.org/3/library/xml.etree.elementtree.html#tutorial). It might be worth noting that, from Python 3.8 onwards and as shown in the code, you can use `{*}` in the XPath argument of `findall` to match any namespace. This is quite helpful for SALT proposal XML, as its elements have a variety of namespaces.

### Resubmitting the proposal

The updated proposal is resubmitted with the `submit` function.

```{literalinclude} ../docs_src/quickstart/resubmission.py
---
language: python
lines: 72-82
emphasize-lines: 8
---
```

The `submit` function returns a submission identifier, which we'll make good use of in the next section.

### Watching the proposal submission progress

Proposal submissions can take a while. The `submit` function does not wait for the submission to finish, but instead returns a unique identifier, which can be used together with the `submission_progress` function to watch the submission progress.

```{literalinclude} ../docs_src/quickstart/resubmission.py
---
language: python
lines: 60-69
emphasize-lines: 3
---
```

Note that `submission_progress` returns an async generator, which explains why an async for loop (rather than a normal for loop) must be used in the code.
