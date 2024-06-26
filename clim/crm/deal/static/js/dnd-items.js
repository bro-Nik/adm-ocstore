(() => {
  let currentDroppable = null;
  let placeholder;
  let isDraggingStarted = false;
  let movingElement;

  const processEmptySections = () => {
    // Create not visible .board-item in empty sections to dnd work with it too
    document
      .querySelectorAll(".board-column-content-wrapper")
      .forEach((section) => {
        if (
          !section.querySelector(".board-item:not(.emptySectionHiddenLesson)")
        ) {
          const emptySectionHiddenLesson = document.createElement("div");
          emptySectionHiddenLesson.classList.add(
            "board-item",
            "emptySectionHiddenLesson"
          );
          section.append(emptySectionHiddenLesson);
        } else {
          const emptySectionHiddenLesson = section.querySelector(
            ".emptySectionHiddenLesson"
          );
          emptySectionHiddenLesson &&
            section.removeChild(emptySectionHiddenLesson);
        }
      });
  };

  const createPlaceholder = () => {
    // Create and position placeholder before movingElement
    placeholder = document.createElement("div");
    placeholder.classList.add("placeholder-kanban");
    movingElement.parentNode.insertBefore(placeholder, movingElement);
  };

  const onMouseMove = (event) => {
    if (!isDraggingStarted) {
      isDraggingStarted = true;
      createPlaceholder();
      Object.assign(movingElement.style, {
        position: "absolute",
        zIndex: 1000,
        left: `${initialMovingElementPageXY.x}px`,
        top: `${initialMovingElementPageXY.y}px`,
      });
    }
    moveAt(movingElement, event.pageX, event.pageY);

    elementBelow = getElementBelow(movingElement, "by-center");
    if (!elementBelow) return;
    let droppableBelow = elementBelow.closest(".board-item");
    if (currentDroppable != droppableBelow) {
      //  currentDroppable=null
      //    if we were not over a droppable element before this event
      //  droppableBelow=null
      //    if we are not over a droppable element now, during this event
      currentDroppable = droppableBelow;
      if (currentDroppable) {
        if (
          !isAbove(movingElement, currentDroppable) ||
          currentDroppable.classList.contains("emptySectionHiddenLesson")
        ) {
          currentDroppable.parentNode.insertBefore(
            placeholder,
            currentDroppable
          );
        } else {
          currentDroppable.parentNode.insertBefore(
            placeholder,
            currentDroppable.nextElementSibling
          );
        }
      }
    }
  };

  const setMovingElement = (event) => {
    movingElement = event.target.closest(".board-item");
  };

  const onMouseUp = () => {
    if (!isDraggingStarted) {
      document.removeEventListener("mousemove", onMouseMove);
      movingElement.onmouseup = null;
      return;
    }
    console.log(
      "We move item",
      movingElement,
      "to column",
      placeholder.closest(".column"),
      "before item",
      placeholder.nextElementSibling,
      "after item",
      placeholder.previousElementSibling
    );
    // update border-line
      var color = $(placeholder.closest(".column")).find('.stage-color').val()
      $(movingElement).attr('style', '--crm-kanban-item-color: ' + color)

      // Отправить на сервер сортировку
      var url = "/crm/deal/update_stage";
      var stage_id = $(placeholder.closest(".column")).data('stage');
      var deal_id = $(movingElement).attr('data-item')
      var previous_deal_sort = $(placeholder.previousElementSibling).attr('data-item-sort');
      if (!previous_deal_sort) {previous_deal_sort = 0}
      url += `${url.indexOf("?") > 0 ? "&" : "?"}stage_id=${stage_id}&deal_id=${deal_id}&previous_deal_sort=${previous_deal_sort}`;
      $.get(url);

    placeholder.parentNode.insertBefore(movingElement, placeholder);
    Object.assign(movingElement.style, {
      // position: "static",
      position: "relative",
      left: "auto",
      top: "auto",
      zIndex: "auto",
      transform: "none",
    });
    document.removeEventListener("mousemove", onMouseMove);
    isDraggingStarted = false;
    placeholder && placeholder.parentNode.removeChild(placeholder);
    movingElement.onmouseup = null;
    movingElement = null;

    // Process empty columns without items
    processEmptySections();
  };

  // const onMouseDown = (event) => {
  //   setMovingElement(event);
  //   shifts.set(event.clientX, event.clientY, movingElement);
  //   initialMovingElementPageXY.set(movingElement);
  //   document.addEventListener("mousemove", onMouseMove);
  //   movingElement.onmouseup = onMouseUp;
  // };
  //
  // window.addEventListener("load", () => {
  //   for (const draggableElement of document.querySelectorAll(".board-item")) {
  //     draggableElement.onmousedown = onMouseDown;
  //     draggableElement.ondragstart = () => {
  //       return false;
  //     };
  //   }
  // });

  $("body").on("mousedown", ".board-item", function (event) {
    setMovingElement(event);
    shifts.set(event.clientX, event.clientY, movingElement);
    initialMovingElementPageXY.set(movingElement);
    document.addEventListener("mousemove", onMouseMove);
    movingElement.onmouseup = onMouseUp;
  })
})();
