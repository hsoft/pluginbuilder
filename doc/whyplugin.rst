Why plugins instead of apps?
============================

Why embedding a Python plugin into an Objective-C application rather than the other way around
(driving the Objective-C runtime from Python)? I wrote an `article about that <http://www.hardcoded.net/articles/embedded-pyobjc.htm>`__ a while ago. Here's an excerpt:

**Speed.** In a GUI application, there's usually many, *many* calls being made all the time by the different elements of the GUI. For example, ``NSTableView``'s datasource and delegate methods are called tons of times at each redraw. Each calls having to pass through the PyObjC bridge is inherently slower than a native call. While machines are usually fast enough for this not to be noticeable most of the time, there might be situations where it's not the case, scrolling a large list for example.

I have no benchmarks to back this. All I can tell you is that my first PyObjC application, musicGuru, was initially all Python. Scrolling was sluggish and I decided to give the Embedded Way a try. It fixed the problem and I never looked back again.

**Integration.** Although XCode and Interface Builder offer Python integration (and since I never used them, I don't know if it works well), there's no doubt that Apple's efforts are much more axed on Objective-C. Auto-completion, help, build process, these are all designed with Objective-C in mind.

**Memory usage.** Since PyObjC 2.0, metadata from Apple's bridge support files are loaded in memory, leading to pretty high initial memory usage (as I mentioned in `my article about 64-bit PyObjC applications <http://www.hardcoded.net/articles/building-64-bit-pyobjc-applications-with-py2app.htm>`__). When you embed Python in your Objective-C application, it usually means that your Python code use fewer Objective-C classes, thus allowing you to use neat tricks to reduce that memory usage. I'm talking about saving tens of MB of initial memory usage here, so it's not negligible.
