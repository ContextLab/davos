# ADD DOCSTRING


class DotDict(dict):
    # ADD DOCSTRING
    # simple helper that allows a dict to be accessed like a JS object
    __delattr__ = dict.__delitem__
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

    def __init__(self, d):
        # ADD DOCSTRING
        for k, v in d.items():
            if isinstance(v, dict):
                v = DotDict(v)
            self[k] = v


JS_FUNCTIONS = DotDict({
    'jupyter': {
        'restartRunAbove': """
            function restartRunCellsAbove(){
                const notebook = Jupyter.notebook,
                    anchorCellIndex = notebook.get_anchor_index(),
                    selectedCellIndex = notebook.get_selected_index(),
                    runningCellElement = document.getElementsByClassName('cell running')[0],
                    allCellElements = notebook.get_cell_elements(),
                    runningCellIndex = allCellElements.index(runningCellElement);

                function queueCellsAndReselect() {
                    notebook.execute_cell_range(0, runningCellIndex + 1);
                    notebook.select(anchorCellIndex);
                    if (selectedCellIndex !== anchorCellIndex) {
                        notebook.select(selectedCellIndex, false);
                    }
                }

                notebook.kernel.restart(queueCellsAndReselect);
            }
        """
    }
})
