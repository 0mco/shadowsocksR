# Procedure
    main:
        * parse config
        * connect to daemon, if daemon is not started, start it in another thread and connect to it
        * parse command and send command to daemon
        * receive result and print to console

    daemon:
        * redirect the stdout output to other steam
        * daemonize
        * start socket loop
        * for each request, execute the command and return the result in json
