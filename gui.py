from sequence.gui.run_gui import RunGui

if __name__ == '__main__':
    gui = RunGui('Test Project')
    gui.load_graph()
    gui.gui.run_server(debug=False, host="127.0.0.1", port="8050")
