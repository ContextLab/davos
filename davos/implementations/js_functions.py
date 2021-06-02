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
        'restartRunCellsAbove': """\
            const restartRunCellsAbove = function() {
                const outputArea = this,
                    notebook = Jupyter.notebook,
                    // first cell currently selected, if multiple
                    anchorCellIndex = notebook.get_anchor_index(),
                    // most recently selected cell, if multiple
                    selectedCellIndex = notebook.get_selected_index(),
                    runningCell = outputArea.element.parents('.cell'),
                    allCells = notebook.get_cell_elements(),
                    runningCellIndex = allCells.index(runningCell);

                const queueCellsAndResetSelection = function() {
                    notebook.execute_cell_range(0, runningCellIndex + 1);
                    notebook.select(anchorCellIndex);
                    if (selectedCellIndex !== anchorCellIndex) {
                        // select multiple cells without moving anchor
                        notebook.select(selectedCellIndex, false);
                    }
                }

                notebook.kernel.restart(queueCellsAndResetSelection);
            }.bind(this)
        """,
        'displayButtonPrompt': """\
            const displayPromptButton = function(buttonText, onClick) {
                buttonText = (typeof buttonText !== 'undefined') ? buttonText : '';
                onClick = (typeof onClick !== 'undefined') ? onClick : () => console.log('clicked');
                const runningCell = this.element.parents('.cell'),
                    buttonElement = document.createElement('BUTTON');
                buttonElement.classList.add('davos', 'prompt-button');
                buttonElement.textContent = buttonText;
                buttonElement.addEventListener('click', )
                
            }.bind(this)
        """
    }
})
