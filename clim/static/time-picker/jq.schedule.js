"use strict";

function _typeof(obj) { "@babel/helpers - typeof"; return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function (obj) { return typeof obj; } : function (obj) { return obj && "function" == typeof Symbol && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }, _typeof(obj); }


(function ($) {
  'use strict';

  var PLUGIN_NAME = 'jqSchedule';
  var methods = {
    /**
     *
     * @param {string} str
     * @returns {number}
     */
    calcStringTime: function calcStringTime(str) {
      var slice = str.split(':');
      var h = Number(slice[0]) * 60 * 60;
      var i = Number(slice[1]) * 60;
      return h + i;
    },

    /**
     *
     * @param {number} val
     * @returns {string}
     */
    formatTime: function formatTime(val) {
      var i1 = val % 3600;
      var h = '' + Math.floor(val / 36000) + Math.floor(val / 3600 % 10);
      var i = '' + Math.floor(i1 / 600) + Math.floor(i1 / 60 % 10);
      return h + ':' + i;
    },

    /**
     *
     * @param {number} val
     * @returns {string}
     */
    formatTimeHours: function formatTimeHours(sec, secInDay) {
      // console.log(setting)
      if (sec >= 2 * secInDay) {
        var d = '' + parseInt(sec / secInDay);
        var h = ' ' + parseInt(sec % secInDay / 3600);
        return d + ' д' + (h > 0 ? h + ' ч': '') ;

      } else {
        var i1 = sec % 3600;
        var h = '' + parseInt(sec / 3600);
        var i = '' + Math.floor(i1 / 600) + Math.floor(i1 / 60 % 10);
        return (h > 0 ? h + ' ч' : '')+ ((h > 0 && i>0) ? ' ' : '') + (i > 0 ? i + ' мин' : '');
      }
    },

    /**
     *
     * @param {date} date
     * @returns {integer}
     */
    differenceOfDays: function differenceOfDays(date1, date2) {
      var num = (date2 - date1) / (1000 * 3600 * 24);
      return Math.abs(num)
    },

    /** 
     * Высчитывает дату от начала таблицы
     */
    diffDaysToDate: function diffDaysToDate(tableStartDate, diff) {

        var date = new Date(tableStartDate)
        date = new Date(date.setDate(date.getDate() + diff))
        date = date.toLocaleDateString('en-ca');

        return date;
    },

    /**
     * Сохранить данные настройки
     *
     * @param {Options} data
     * @returns {*}
     */
    _saveSettingData: function _saveSettingData(data) {
      return this.data(PLUGIN_NAME + 'Setting', data);
    },

    /**
     * Получить данные конфигурации
     *
     * @returns Options
     */
    _loadSettingData: function _loadSettingData() {
      return this.data(PLUGIN_NAME + 'Setting');
    },

    /**
     * Сохранение сохраненных данных
     *
     * @param {SaveData} data
     * @returns {*}
     */
    _saveData: function _saveData(data) {
      var d = $.extend({
        tableStartTime: 0,
        tableEndTime: 0,
        tableStartDate: data.tableStartDate,
        tableEndDate: data.tableEndDate,
        schedule: [],
        timeline: []
      }, data);
      return this.data(PLUGIN_NAME, d);
    },

    /**
     * Извлечение сохраненных данных
     *
     * @returns SaveData
     */
    _loadData: function _loadData() {
      return this.data(PLUGIN_NAME);
    },

    /**
     * スケジュールの取得
     *
     * @returns ScheduleData[]
     */
    scheduleData: function scheduleData() {
      var $this = $(this);

      var saveData = methods._loadData.apply($this);

      if (saveData) {
        return saveData.schedule;
      }

      return [];
    },

    /**
     * get timelineData
     * @returns {any[]}
     */
    timelineData: function timelineData() {
      var $this = $(this);

      var saveData = methods._loadData.apply($this);

      var data = [];
      var i;

      for (i in saveData.timeline) {
        data[i] = saveData.timeline[i];
        data[i].schedule = [];
      }

      for (i in saveData.schedule) {
        var d = saveData.schedule[i];

        if (typeof d.timeline === 'undefined') {
          continue;
        }

        if (typeof data[d.timeline] === 'undefined') {
          continue;
        }

        data[d.timeline].schedule.push(d);
      }

      return data;
    },

    /**
     * get timelineData New added
     * @returns {any[]}
     */
    timelineNewData: function timelineNewData() {
      var $this = $(this);

      var saveData = methods._loadData.apply($this);
      var tableStartDate = saveData.tableStartDate

      var data = [];
      var i;

      for (i in saveData.timeline) {
        data[i] = saveData.timeline[i];
        data[i].schedule = [];
      }

      for (i in saveData.schedule) {
        var d = saveData.schedule[i];
        if (!d.new_schedule && !d.changed) {
          continue;
        }

        if (typeof d.timeline === 'undefined') {
          continue;
        }

        if (typeof data[d.timeline] === 'undefined') {
          continue;
        }

        data[d.timeline].schedule.push(d);
      }

      return data;
    },


     /**
     * reset data
     */
    resetData: function resetData() {
      return this.each(function () {
        var $this = $(this);

        var saveData = methods._loadData.apply($this);

        saveData.schedule = [];

        methods._saveData.apply($this, [saveData]);

        $this.find('.sc_bar').remove();

        for (var i in saveData.timeline) {
          saveData.timeline[i].schedule = [];

          methods._resizeRow.apply($this, [i, 0]);
        }

        methods._saveData.apply($this, [saveData]);
      });
    },

     /**
     * reset new data
     */
    resetNewData: function resetNewData() {
      return this.each(function () {
        var $this = $(this);

        var saveData = methods._loadData.apply($this);

        for (var i in saveData.schedule) {
          if (saveData.schedule[i].new_schedule) {
            saveData.schedule[i] = []
          }
        }

        methods._saveData.apply($this, [saveData]);

        $this.find('.sc_bar').each(function() {
          if ($(this).hasClass('sc_bar_insert')) {
            $(this).remove()
          }
        });

        methods._saveData.apply($this, [saveData]);
      });
    },

     /**
     * reset data in deal
     */
    resetDataInDeal: function resetDataInDeal() {
      return this.each(function () {
        var $this = $(this);

        var saveData = methods._loadData.apply($this);

        for (var i in saveData.schedule) {
          if (saveData.schedule[i].new_schedule) {
            saveData.schedule[i] = []
          }
          if (saveData.schedule[i].event === event) {
            saveData.schedule[i].delete = true;
            saveData.schedule[i].changed = true;
          }
        }

        methods._saveData.apply($this, [saveData]);

        $this.find('.sc_bar').each(function() {
          if ($(this).hasClass('sc_bar_insert') || !$(this).hasClass('ui-draggable-disabled')) {
            $(this).remove()
          }
        });

        // methods._saveData.apply($this, [saveData]);
      });
    },

    /**
     * Добавляет новый участок времени
     * add schedule data
     *
     * @param {number} timeline
     * @param {object} data
     * @returns {methods}
     */
    addSchedule: function addSchedule(timeline, data) {
      return this.each(function () {
        var $this = $(this);
        var d = {
          start: data.start,
          end: data.end,
          event: data.event,
          startTime: methods.calcStringTime(data.start),
          endTime: methods.calcStringTime(data.end),
          startDate: data.day,
          endDate: data.day,
          text: data.text,
          timeline: timeline,
          new_schedule: true
        };

        if (data.data) {
          d.data = data.data;
        }

        methods._addScheduleData.apply($this, [timeline, d]);

        methods._resetBarPosition.apply($this, [timeline]);
      });
    },

     /**
     * add schedule data
     *
     * @param {number} timeline
     * @param {object} data
     * @returns {methods}
     */
    addRow: function addRow(timeline, data) {
      return this.each(function () {
        var $this = $(this);

        methods._addRow.apply($this, [timeline, data]);
      });
    },

     /**
     * clear row
     *
     * @returns {methods}
     */
    resetRowData: function resetRowData() {
      return this.each(function () {
        var $this = $(this);

        var data = methods._loadData.apply($this);

        data.schedule = [];
        data.timeline = [];

        methods._saveData.apply($this, [data]);

        $this.find('.sc_bar').remove();
        $this.find('.timeline').remove();
        $this.find('.sc_data').height(0);
      });
    },

     /**
     * clear days
     *
     * @returns {methods}
     */
    resetDays: function resetDays() {
      return this.each(function () {
        var $this = $(this);
        $this.find('.sc_header_scroll').empty();
      });
    },

   /**
     * clear row
     *
     * @param {object} data
     * @returns {methods}
     */
    setRows: function setRows(data) {
      return this.each(function () {
        var $this = $(this);
        methods.resetRowData.apply($this, []);

        for (var timeline in data) {
          methods.addRow.apply($this, [timeline, data[timeline]]);
        }
      });
    },

   /**
     * create days
     *
     * 
     * 
     */
    setDays: function setDays(start) {
      return this.each(function () {
        var $this = $(this);
        methods.resetDays.apply($this);
        var setting = methods._loadSettingData.apply($this);

        var saveData = methods._loadData.apply($this);
        var tableStartTime = saveData.tableStartTime
        var tableEndTime = saveData.tableEndTime

        var startDate = new Date(start);
        var endDate = new Date(startDate);
        var endDate = new Date(endDate.setDate(endDate.getDate() + 14));


        for (var day = new Date(startDate); day < endDate; day = new Date(day.setDate(day.getDate() + 1))) {
          var html_day = '';
          html_day += '<div class="sc_day"></div>';
          var $day = $(html_day);
          if (day.getDay() < 1 || day.getDay() > 5) {
            $day.addClass('weekend');
          }

          var html_date = '<div class="sc_date">' + day.toLocaleString('ru', { year: 'numeric', month: 'long', day: 'numeric'}) + '</div>';

          var $date = $(html_date);

          var html_time_in_day = '<div class="sc_time_in_day"></div>';
          var $time_in_day = $(html_time_in_day);

          var beforeTime = -1;

          //alert(saveData.widthTime)
          for (var t = tableStartTime; t < tableEndTime; t += setting.widthTime) {
            if (beforeTime < 0 || Math.floor(beforeTime / 3600) !== Math.floor(t / 3600)) {
              var html = '';
              html += '<div class="sc_time">' + methods.formatTime(t) + '</div>';
              var $time = $(html);
              var cn = Number(Math.min(Math.ceil((t + setting.widthTime) / 3600) * 3600, tableEndTime) - t);
              var cellNum = Math.floor(cn / setting.widthTime);
              $time.width(cellNum * setting.widthTimeX);
              $time_in_day.append($time);
              beforeTime = t;
            }
          }
          //$day.width(cellNum * config.widthTimeX);
          $day.append($date);
          $day.append($time_in_day);
          $this.find('.sc_header_scroll').append($day);

        // methods._saveData.apply($this, [{
        //   tableStartTime: tableStartTime,
        //   tableEndTime: tableEndTime,
        //   tableStartDate: startDate,
        //   tableEndDate: endDate
        // }]);
        saveData.tableStartDate = startDate;
        saveData.tableEndDate = endDate;
        }
      });
    },

    /**
     * switch draggable
     * @param {boolean} enable
     */
    setDraggable: function setDraggable(enable) {
      return this.each(function () {
        var $this = $(this);

        var setting = methods._loadSettingData.apply($this);

        if (enable !== setting.draggable) {
          setting.draggable = enable;

          methods._saveSettingData.apply($this, setting);

          if (enable) {
            $this.find('.sc_bar').draggable('enable');
          } else {
            $this.find('.sc_bar').draggable('disable');
          }
        }
      });
    },

    /**
     * Получить текущий номер временной шкалы
     *
     * @param node
     * @param top
     * @returns {number}
     */
    _getTimeLineNumber: function _getTimeLineNumber(node, top) {
      var $this = $(this);

      var setting = methods._loadSettingData.apply($this);

      var num = 0;
      var n = 0;
      var tn = Math.ceil(top / (setting.timeLineY + setting.timeLinePaddingTop + setting.timeLinePaddingBottom));

      for (var i in setting.rows) {
        var r = setting.rows[i];
        var tr = 0;

        if (_typeof(r.schedule) === 'object') {
          tr = r.schedule.length;
        }

        if (node && node.timeline) {
          tr++;
        }

        n += Math.max(tr, 1);

        if (n >= tn) {
          break;
        }

        num++;
      }

      return num;
    },

    /**
     * Добавить фоновые данные
     *
     * @param {ScheduleData} data
     */
    // _addScheduleBgData: function _addScheduleBgData(data) {
    //   return this.each(function () {
    //     var $this = $(this);
    //
    //     var setting = methods._loadSettingData.apply($this);
    //
    //     var saveData = methods._loadData.apply($this);
    //
    //     var st = Math.ceil((data.startTime - saveData.tableStartTime) / setting.widthTime);
    //     var et = Math.floor((data.endTime - saveData.tableStartTime) / setting.widthTime);
    //     var $bar = $('<div class="sc_bgBar"><span class="text"></span></div>');
    //     $bar.css({
    //       left: st * setting.widthTimeX,
    //       top: 0,
    //       width: (et - st) * setting.widthTimeX,
    //       height: $this.find('.sc_main .timeline').eq(data.timeline).height()
    //     });
    //
    //     if (data.text) {
    //       $bar.find('.text').text(data.text);
    //     }
    //
    //     if (data.class) {
    //       $bar.addClass(data.class);
    //     } // $element.find('.sc_main').append($bar);
    //
    //
    //     $this.find('.sc_main .timeline').eq(data.timeline).append($bar);
    //   });
    // },

    /**
     * Добавить расписание
     *
     * @param timeline
     * @param {ScheduleData} d
     * @returns {number}
     */
    _addScheduleData: function _addScheduleData(timeline, d) {
      var data = d;
      data.startTime = data.startTime ? data.startTime : methods.calcStringTime(data.start);
      data.endTime = data.endTime ? data.endTime : methods.calcStringTime(data.end);


      return this.each(function () {
        var $this = $(this);

        var setting = methods._loadSettingData.apply($this);

        var saveData = methods._loadData.apply($this);

        var st = Math.ceil((data.startTime - saveData.tableStartTime) / setting.widthTime);
        var et = Math.floor((data.endTime - saveData.tableStartTime) / setting.widthTime);
        var $bar = $('<div class="sc_bar"><span class="head"><span class="time"></span></span><span class="text"></span></div>');
        if (!data.new_schedule && (data.event !== event)) {
        //alert(!data.new_schedule || (deal_id && (parseInt(data.dealId) !== deal_id)))
          $bar.attr('data-disabled', true)
          $bar.addClass('ui-draggable-disabled ui-resizable-disabled ui-state-disabled')
          // $bar.find('.ui-resizable-handle').attr('style', 'z-index: 90');
          //$bar.draggable('disable')
            // $($bar).draggable('disable');
        }

        var stext = methods.formatTime(data.startTime);
        var etext = methods.formatTime(data.endTime);

        var snum = methods._getScheduleCount.apply($this, [data.timeline]);

        var tl_in_day = $('.dayline').eq(1).find('.tl').length;
        var startDate = new Date(data.startDate);
        if (startDate < saveData.tableStartDate) {
          startDate = new Date(saveData.tableStartDate);
          st = 0;
          stext = methods.formatTime(saveData.tableStartTime);
        }
        var endDate = new Date(data.endDate);
        // if (endDate - saveData.tableEndDate >= 0) {
        //   alert('>')
        //   endDate = new Date(saveData.tableEndDate);
        //   endDate = new Date(endDate.setDate(endDate.getDate() - 1));
        // }
         // day = new Date(day.setDate(day.getDate() + 1))
        var width = methods.differenceOfDays(startDate, endDate) * tl_in_day * setting.widthTimeX + (et - st) * setting.widthTimeX;

        $bar.css({
          left: tl_in_day * methods.differenceOfDays(saveData.tableStartDate, startDate) * setting.widthTimeX + st * setting.widthTimeX,
          // left: st * setting.widthTimeX,
          top: snum * setting.timeLineY + setting.timeLinePaddingTop,
          width: width,
          height: setting.timeLineY
        });
        var duration = data.endTime - data.startTime + methods.differenceOfDays(startDate, endDate) * tl_in_day * setting.widthTime;
        duration = methods.formatTimeHours(duration, tl_in_day * setting.widthTime)
        $bar.find('.time').text(stext + '-' + etext + ' (' + duration + ')');

        if (data.text) {
          $bar.find('.text').text(data.text);
        }

        if (data.class) {
          $bar.addClass(data.class);
        } // $this.find('.sc_main').append($bar);

        var $row = $this.find('.sc_main .timeline').eq(timeline);
        $row.append($bar); // データの追加

        saveData.schedule.push(data);

        methods._saveData.apply($this, [saveData]); // コールバックがセットされていたら呼出


        if (setting.onAppendSchedule) {
          setting.onAppendSchedule.apply($this, [$bar, data]);
        } // key


        var key = saveData.schedule.length - 1;
        $bar.data('sc_key', key);
        $bar.on('mouseup', function () {
          // コールバックがセットされていたら呼出
          if (setting.onClick) {
            if ($(this).data('dragCheck') !== true && $(this).data('resizeCheck') !== true) {
              var $n = $(this);
              var scKey = $n.data('sc_key');
              setting.onClick.apply($this, [$n, saveData.schedule[scKey]]);
            }
          }
        });

        var $node = $this.find('.sc_bar');
        var currentNode = null; // move node.

        $node.draggable({
          grid: [setting.widthTimeX, 1],
          containment: $this.find('.sc_main'),
          helper: 'original',
          start: function start(event, ui) {
            var node = {};
            node.node = this;
            node.offsetTop = ui.position.top;
            node.offsetLeft = ui.position.left;
            node.currentTop = ui.position.top;
            node.currentLeft = ui.position.left;
            node.timeline = methods._getTimeLineNumber.apply($this, [currentNode, ui.position.top]);
            node.nowTimeline = node.timeline;
            currentNode = node;
          },

          /**
           *
           * @param {Event} event
           * @param {function} ui
           * @returns {boolean}
           */
          drag: function drag(event, ui) {
            $(this).data('dragCheck', true);
            if ($(this).attr('data-disabled')) {
              return false;
            }

            if (!currentNode) {
              return false;
            }

            var $moveNode = $(this);
            var scKey = $moveNode.data('sc_key');

            var timelineNum = methods._getTimeLineNumber.apply($this, [currentNode, ui.position.top]); // eslint-disable-next-line no-param-reassign


            ui.position.left = Math.floor(ui.position.left / setting.widthTimeX) * setting.widthTimeX;

            if (currentNode.nowTimeline !== timelineNum) {
              // 現在のタイムライン
              currentNode.nowTimeline = timelineNum;
            }

            currentNode.currentTop = ui.position.top;
            currentNode.currentLeft = ui.position.left; // テキスト変更

            methods._rewriteBarText.apply($this, [$moveNode, saveData.schedule[scKey]]);

            return true;
          },
          // 要素の移動が終った後の処理
          stop: function stop() {
            $(this).data('dragCheck', true);
            if ($(this).attr('data-disabled')) {
              return false;
            }
            $(this).data('dragCheck', false);
            currentNode = null;
            var $n = $(this);
            var scKey = $n.data('sc_key');
            var x = $n.position().left; 
            var w = $n.width();

            var tl_in_day = $('.dayline').eq(1).find('.tl').length;

            var startDiff = parseInt(x / (tl_in_day * setting.widthTimeX));
            var startDate = methods.diffDaysToDate(saveData.tableStartDate, startDiff);
            var endDiff = parseInt((x + w) / (tl_in_day * setting.widthTimeX));
            var endDate = methods.diffDaysToDate(saveData.tableStartDate, endDiff);

            // var start = saveData.tableStartTime + Math.floor(x / setting.widthTimeX) * setting.widthTime; 
            var start = saveData.tableStartTime + (Math.floor(x / setting.widthTimeX) - startDiff * tl_in_day) * setting.widthTime; 
            var end = saveData.tableStartTime + (Math.floor((x + w) / setting.widthTimeX) - endDiff * tl_in_day) * setting.widthTime;

            saveData.schedule[scKey].startDate = startDate;
            saveData.schedule[scKey].endDate = endDate;
            saveData.schedule[scKey].start = methods.formatTime(start);
            saveData.schedule[scKey].end = methods.formatTime(end);
            saveData.schedule[scKey].startTime = start;
            saveData.schedule[scKey].endTime = end; // コールバックがセットされていたら呼出
            saveData.schedule[scKey].changed = true;


            if (setting.onChange) {
              setting.onChange.apply($this, [$n, saveData.schedule[scKey]]);
            }
          }
        });
        var resizableHandles = ['e'];

        if (setting.resizableLeft) {
          resizableHandles.push('w');
        }

        $node.resizable({
          handles: resizableHandles.join(','),
          grid: [setting.widthTimeX, setting.timeLineY - setting.timeBorder],
          minWidth: setting.widthTimeX,
          containment: $this.find('.sc_main_scroll'),
          start: function start() {
            var $n = $(this);
            $n.data('resizeCheck', true);
          },
          resize: function resize(ev, ui) {
            // box-sizing: border-box; に対応
            ui.element.height(ui.size.height);
            if (ui.size.width < 30) {
              ui.element.width(30);
            } else {
              ui.element.width(ui.size.width);
            }

            var $resizeNode = $(this);
            var scKey = $resizeNode.data('sc_key');
            methods._rewriteBarText.apply($this, [$resizeNode, saveData.schedule[scKey]]);
          },
          // 要素の移動が終った後の処理
          stop: function stop() {
            var $n = $(this);
            var scKey = $n.data('sc_key');
            var x = $n.position().left;
            var w = $n.outerWidth();

            var tl_in_day = $('.dayline').eq(1).find('.tl').length;

            var startDiff = parseInt(x / (tl_in_day * setting.widthTimeX));
            var startDate = methods.diffDaysToDate(saveData.tableStartDate, startDiff)
            var endDiff = parseInt((x + w) / (tl_in_day * setting.widthTimeX));
            var endDate = methods.diffDaysToDate(saveData.tableStartDate, endDiff)

            var start = saveData.tableStartTime + (Math.floor(x / setting.widthTimeX) - startDiff * tl_in_day) * setting.widthTime; 
            var end = saveData.tableStartTime + (Math.floor((x + w) / setting.widthTimeX) - endDiff * tl_in_day) * setting.widthTime;

            // var start = saveData.tableStartTime + Math.floor(x / setting.widthTimeX) * setting.widthTime;
            // var end = saveData.tableStartTime + Math.floor((x + w) / setting.widthTimeX) * setting.widthTime;
            var timelineNum = saveData.schedule[scKey].timeline;
            saveData.schedule[scKey].startDate = startDate;
            saveData.schedule[scKey].endDate = endDate;
            saveData.schedule[scKey].start = methods.formatTime(start);
            saveData.schedule[scKey].end = methods.formatTime(end);
            saveData.schedule[scKey].startTime = start;
            saveData.schedule[scKey].endTime = end; // 高さ調整
            saveData.schedule[scKey].changed = true;

            methods._resetBarPosition.apply($this, [timelineNum]); // テキスト変更


            methods._rewriteBarText.apply($this, [$n, saveData.schedule[scKey]]);

            $n.data('resizeCheck', false); // コールバックがセットされていたら呼出

            if (setting.onChange) {
              setting.onChange.apply($this, [$n, saveData.schedule[scKey]]);
            }
          }
        });

        if (setting.draggable === false) {
          $node.draggable('disable');
        }

        if (setting.resizable === false) {
          $node.resizable('disable');
        }

        return key;
      });
    },

    /**
     * Получить количество расписаний
     *
     * @param {number} n row number
     * @returns {number}
     */
    _getScheduleCount: function _getScheduleCount(n) {
      var $this = $(this);

      var saveData = methods._loadData.apply($this);

      var num = 0;

      for (var i in saveData.schedule) {
        if (saveData.schedule[i].timeline === n) {
          num++;
        }
      }

      return num;
    },

    /**
     * add rows
     *
     * @param timeline
     * @param row
     */
    _addRow: function _addRow(timeline, row) {
      return this.each(function () {
        var $this = $(this);

        var setting = methods._loadSettingData.apply($this);

        var saveData = methods._loadData.apply($this);

        var id = $this.find('.sc_main .timeline').length;
        var html;
        html = '';
        html += '<div class="timeline"></div>';
        var $data = $(html);

        if (row.title) {
          $data.append('<span class="timeline-title">' + row.title + '</span>');
        }

        if (row.subtitle) {
          $data.append('<span class="timeline-subtitle">' + row.subtitle + '</span>');
        } // event call


        if (setting.onInitRow) {
          setting.onInitRow.apply($this, [$data, row]);
        }

        $this.find('.sc_data_scroll').append($data);
        html = '';
        html += '<div class="timeline"></div>';
        var $timeline = $(html);

        var tableStartDate = saveData.tableStartDate;
        var tableEndDate = saveData.tableEndDate;

        for (var day = new Date(tableStartDate); day < tableEndDate; day = new Date(day.setDate(day.getDate() + 1))) {
          // var html_dayline = '<div class="dayline" data-date="' + day.toLocaleDateString('en-ca') + '"></div>';
          var html_dayline = '<div class="dayline"></div>';
          var $dayline = $(html_dayline);
          if (day.getDay() < 1 || day.getDay() > 5) {
            $dayline.addClass('weekend')
          }

          for (var t = saveData.tableStartTime; t < saveData.tableEndTime; t += setting.widthTime) {
            var $tl = $('<div class="tl"></div>');
            $tl.outerWidth(setting.widthTimeX);
            $tl.data('time', methods.formatTime(t));
            $tl.data('day', day.toLocaleDateString('en-ca'));
            $tl.data('timeline', timeline);
            $dayline.append($tl);
          } // クリックイベント
            $timeline.append($dayline);
        }


        // left click
        $timeline.find('.tl').on('click', function () {
          if (setting.onScheduleClick) {
            setting.onScheduleClick.apply($this, [this, $(this).data('time'), $(this).data('day'),$(this).data('timeline'), saveData.timeline[$(this).data('timeline')]]);
          }
        });

        // right click
        $timeline.find('.tl').on('contextmenu', function () {
          if (setting.onScheduleClick) {
            setting.onScheduleClick.apply($this, [this, $(this).data('time'), $(this).data('timeline'), saveData.timeline[$(this).data('timeline')]]);
          }

          return false;
        });
        $this.find('.sc_main').append($timeline);
        saveData.timeline[timeline] = row;

        methods._saveData.apply($this, [saveData]);

        if (row.class && row.class !== '') {
          $this.find('.sc_data .timeline').eq(id).addClass(row.class);
          $this.find('.sc_main .timeline').eq(id).addClass(row.class);
        } // график графика


        if (row.schedule) {
          for (var i in row.schedule) {
            var bdata = row.schedule[i];
            var s = bdata.start ? bdata.start : methods.calcStringTime(bdata.startTime);
            var e = bdata.end ? bdata.end : methods.calcStringTime(bdata.endTime);
            var data = {};
            data.start = s;
            data.end = e;

            data.startDate = bdata.date_start;
            data.endDate = bdata.date_end;
            data.event = bdata.event;
            data.employmentId = bdata.employment_id;
            data.changed = false;

            if (bdata.text) {
              data.text = bdata.text;
            }

            data.timeline = timeline;
            data.data = {};

            if (bdata.data) {
              data.data = bdata.data;
            }

            methods._addScheduleData.apply($this, [id, data]);
          }
        } // Регулировка высоты


        methods._resetBarPosition.apply($this, [id]);

        $this.find('.sc_main .timeline').eq(id).droppable({
          accept: '.sc_bar',
          drop: function drop(ev, ui) {
            var node = ui.draggable;
            var scKey = node.data('sc_key');
            var nowTimelineNum = saveData.schedule[scKey].timeline;
            var timelineNum = $this.find('.sc_main .timeline').index(this); // タイムラインの変更

            saveData.schedule[scKey].timeline = timelineNum;
            node.appendTo(this); // 高さ調整

            methods._resetBarPosition.apply($this, [nowTimelineNum]);

            methods._resetBarPosition.apply($this, [timelineNum]);
          }
        }); // Вызвать, если установлен обратный вызов

        if (setting.onAppendRow) {
          $this.find('.sc_main .timeline').eq(id).find('.sc_bar').each(function () {
            var $n = $(this);
            var scKey = $n.data('sc_key');
            setting.onAppendRow.apply($this, [$n, saveData.schedule[scKey]]);
          });
        }
      });
    },

    /**
     * Изменить текст
     *
     * @param {jQuery} node
     * @param {Object} data
     */
    _rewriteBarText: function _rewriteBarText(node, data) {
      return this.each(function () {
        var $this = $(this);

        var setting = methods._loadSettingData.apply($this);
        var saveData = methods._loadData.apply($this);

        var x = node.position().left;
        var w = node.width();

        var tl_in_day = $('.dayline').eq(1).find('.tl').length;

        var startDiff = parseInt(x / (tl_in_day * setting.widthTimeX));
        var endDiff = parseInt((x + w) / (tl_in_day * setting.widthTimeX));

        var start = saveData.tableStartTime + (Math.floor(x / setting.widthTimeX) - startDiff * tl_in_day) * setting.widthTime; 
        var end = saveData.tableStartTime + (Math.floor((x + w) / setting.widthTimeX) - endDiff * tl_in_day) * setting.widthTime;

        var html = methods.formatTime(start) + '-' + methods.formatTime(end);
        var sec = w / setting.widthTimeX * setting.widthTime
        html += ' (' + methods.formatTimeHours(sec, tl_in_day * setting.widthTime) + ')'
        $(node).find('.time').html(html);
      });
    },

    /**
     *
     * @param {Number} n
     */
    _resetBarPosition: function _resetBarPosition(n) {
      return this.each(function () {
        var $this = $(this);

        var setting = methods._loadSettingData.apply($this); // 要素の並び替え


        var $barList = $this.find('.sc_main .timeline').eq(n).find('.sc_bar');
        var codes = [],
            check = [];
        var h = 0;
        var $e1, $e2;
        var c1, c2, s1, s2, e1, e2;
        var i;

        for (i = 0; i < $barList.length; i++) {
          codes[i] = {
            code: i,
            x: $($barList[i]).position().left
          };
        } // ソート


        codes.sort(function (a, b) {
          if (a.x < b.x) {
            return -1;
          }

          if (a.x > b.x) {
            return 1;
          }

          return 0;
        });

        for (i = 0; i < codes.length; i++) {
          c1 = codes[i].code;
          $e1 = $($barList[c1]);

          for (h = 0; h < check.length; h++) {
            var next = false;

            for (var j = 0; j < check[h].length; j++) {
              c2 = check[h][j];
              $e2 = $($barList[c2]);
              s1 = $e1.position().left;
              e1 = $e1.position().left + $e1.outerWidth();
              s2 = $e2.position().left;
              e2 = $e2.position().left + $e2.outerWidth();

              if (s1 < e2 && e1 > s2) {
                next = true;
                continue;
              }
            }

            if (!next) {
              break;
            }
          }

          if (!check[h]) {
            check[h] = [];
          }

          $e1.css({
            top: h * setting.timeLineY + setting.timeLinePaddingTop
          });
          check[h][check[h].length] = c1;
        } // 高さの調整


        methods._resizeRow.apply($this, [n, check.length]);
      });
    },

    /**
     *
     * @param n
     * @param height
     */
    _resizeRow: function _resizeRow(n, height) {
      return this.each(function () {
        var $this = $(this);

        var setting = methods._loadSettingData.apply($this);

        var h = Math.max(height, 1);
        $this.find('.sc_data .timeline').eq(n).outerHeight(h * setting.timeLineY + setting.timeLineBorder + setting.timeLinePaddingTop + setting.timeLinePaddingBottom);
        $this.find('.sc_main .timeline').eq(n).outerHeight(h * setting.timeLineY + setting.timeLineBorder + setting.timeLinePaddingTop + setting.timeLinePaddingBottom);
        $this.find('.sc_main .timeline').eq(n).find('.sc_bgBar').each(function () {
          $(this).outerHeight($(this).closest('.timeline').outerHeight());
        });
        $this.find('.sc_data').outerHeight($this.find('.sc_main_box').outerHeight());
      });
    },

    /**
     * resizeWindow
     */
    _resizeWindow: function _resizeWindow() {
      return this.each(function () {
        var $this = $(this);

        var setting = methods._loadSettingData.apply($this);

        var saveData = methods._loadData.apply($this);

        var scWidth = $this.width();
        var scMainWidth = scWidth - setting.dataWidth - setting.verticalScrollbar;
        var cellNum = Math.floor((saveData.tableEndTime - saveData.tableStartTime) / setting.widthTime) * 14; // days
        $this.find('.sc_header_cell').width(setting.dataWidth);
        $this.find('.sc_data,.sc_data_scroll').width(setting.dataWidth);
        $this.find('.sc_header').width(scMainWidth);
        $this.find('.sc_main_box').width(scMainWidth);
        $this.find('.sc_header_scroll').width(setting.widthTimeX * cellNum);
        $this.find('.sc_main_scroll').width(setting.widthTimeX * cellNum);
      });
    },

    /**
     * move all cells of the right of the specified time line cell
     *
     * @param timeline
     * @param baseTimeLineCell
     * @param moveWidth
     */
    _moveSchedules: function _moveSchedules(timeline, baseTimeLineCell, moveWidth) {
      return this.each(function () {
        var $this = $(this);

        var setting = methods._loadSettingData.apply($this);

        var saveData = methods._loadData.apply($this);

        var $barList = $this.find('.sc_main .timeline').eq(timeline).find('.sc_bar');

        for (var i = 0; i < $barList.length; i++) {
          var $bar = $($barList[i]);

          if (baseTimeLineCell.position().left <= $bar.position().left) {
            var v1 = $bar.position().left + setting.widthTimeX * moveWidth;
            var v2 = Math.floor((saveData.tableEndTime - saveData.tableStartTime) / setting.widthTime) * setting.widthTimeX - $bar.outerWidth();
            $bar.css({
              left: Math.max(0, Math.min(v1, v2))
            });
            var scKey = $bar.data('sc_key');
            var start = saveData.tableStartTime + Math.floor($bar.position().left / setting.widthTimeX) * setting.widthTime;
            var end = start + (saveData.schedule[scKey].end - saveData.schedule[scKey].start);
            saveData.schedule[scKey].start = methods.formatTime(start);
            saveData.schedule[scKey].end = methods.formatTime(end);
            saveData.schedule[scKey].startTime = start;
            saveData.schedule[scKey].endTime = end;

            methods._rewriteBarText.apply($this, [$bar, saveData.schedule[scKey]]); // if setting


            if (setting.onChange) {
              setting.onChange.apply($this, [$bar, saveData.schedule[scKey]]);
            }
          }
        }

        methods._resetBarPosition.apply($this, [timeline]);
      });
    },

    /**
     * initialize
     */
    init: function init(options) {
      return this.each(function () {
        var $this = $(this);
        var config = $.extend({
          className: 'jq-schedule',
          rows: {},
          startTime: '07:00',
          endTime: '19:30',
          widthTimeX: 15,
          // 1cell辺りの幅(px)
          widthTime: 600,
          // 区切り時間(秒)
          timeLineY: 50,
          // timeline height(px)
          timeLineBorder: 1,
          // timeline height border
          timeBorder: 1,
          // border width
          timeLinePaddingTop: 0,
          timeLinePaddingBottom: 0,
          headTimeBorder: 1,
          // time border width
          dataWidth: 160,
          // data width
          verticalScrollbar: 0,
          // vertical scrollbar width
          bundleMoveWidth: 1,
          // width to move all schedules to the right of the clicked time cell
          draggable: true,
          resizable: true,
          resizableLeft: false,
          // event
          onInitRow: null,
          onChange: null,
          onClick: null,
          onAppendRow: null,
          onAppendSchedule: null,
          onScheduleClick: null
        }, options);

        methods._saveSettingData.apply($this, [config]);

        var tableStartTime = methods.calcStringTime(config.startTime);
        var tableEndTime = methods.calcStringTime(config.endTime);
        tableStartTime -= tableStartTime % config.widthTime;
        tableEndTime -= tableEndTime % config.widthTime;

        var tableStartDate = new Date(config.startDate);
        var tableEndDate = new Date(tableStartDate);
        var tableEndDate = new Date(tableEndDate.setDate(tableEndDate.getDate() + 14));

        methods.differenceOfDays(tableStartDate, tableEndDate)

        methods._saveData.apply($this, [{
          tableStartTime: tableStartTime,
          tableEndTime: tableEndTime,
          tableStartDate: tableStartDate,
          tableEndDate: tableEndDate
        }]);

        // var html = '' + '<div class="sc_menu">' + '\n' + '<div class="sc_header_cell"><span>&nbsp;</span></div>' + '\n' + '<div class="sc_header">' + '\n' + '<div class="sc_header_scroll"></div>' + '\n' + '</div>' + '\n' + '</div>' + '\n' + '<div class="sc_wrapper">' + '\n' + '<div class="sc_data">' + '\n' + '<div class="sc_data_scroll"></div>' + '\n' + '</div>' + '\n' + '<div class="sc_main_box">' + '\n' + '<div class="sc_main_scroll">' + '\n' + '<div class="sc_main"></div>' + '\n' + '</div>' + '\n' + '</div>' + '\n' + '</div>';
        var html = '' + '<div class="sc_menu">' + '\n' + '<div class="sc_header_cell"><span></span></div>' + '\n' + '<div class="sc_header">' + '\n' + '<div class="sc_header_scroll"></div>' + '\n' + '</div>' + '\n' + '</div>' + '\n' + '<div class="sc_wrapper">' + '\n' + '<div class="sc_data">' + '\n' + '<div class="sc_data_scroll"></div>' + '\n' + '</div>' + '\n' + '<div class="sc_main_box">' + '\n' + '<div class="sc_main_scroll">' + '\n' + '<div class="sc_main"></div>' + '\n' + '</div>' + '\n' + '</div>' + '\n' + '</div>';
        $this.append(html);
        $this.addClass(config.className);
        $this.find('.sc_main_box').on('scroll', function () {
          $this.find('.sc_data_scroll').css('top', $(this).scrollTop() * -1);
          $this.find('.sc_header_scroll').css('left', $(this).scrollLeft() * -1);
        }); // add time cell
        // var cellNum = Math.floor((tableEndTime - tableStartTime) / config.widthTime);
        //
        //var date_start = tableStartDate;
        // var date_start = new Date(Date.now());
        
        for (var day = new Date(tableStartDate); day < tableEndDate; day = new Date(day.setDate(day.getDate() + 1))) {
          var html_day = '';
          html_day += '<div class="sc_day"></div>';
          var $day = $(html_day);

          var html_date = '<div class="sc_date">' + day.toLocaleString('ru', { year: 'numeric', month: 'long', day: 'numeric'}) + '</div>';

          var $date = $(html_date);

          var html_time_in_day = '<div class="sc_time_in_day"></div>';
          var $time_in_day = $(html_time_in_day);

          var beforeTime = -1;

          for (var t = tableStartTime; t < tableEndTime; t += config.widthTime) {
            if (beforeTime < 0 || Math.floor(beforeTime / 3600) !== Math.floor(t / 3600)) {
              html = '';
              html += '<div class="sc_time">' + methods.formatTime(t) + '</div>';
              var $time = $(html);
              var cn = Number(Math.min(Math.ceil((t + config.widthTime) / 3600) * 3600, tableEndTime) - t);
              var cellNum = Math.floor(cn / config.widthTime);
              $time.width(cellNum * config.widthTimeX);
              $time_in_day.append($time);
              beforeTime = t;
            }
          }
          //$day.width(cellNum * config.widthTimeX);
          $day.append($date);
          $day.append($time_in_day);
          $this.find('.sc_header_scroll').append($day);

        }


        $(window).on('resize', function () {
          methods._resizeWindow.apply($this);
        }).trigger('resize'); // addrow

        for (var i in config.rows) {
          methods._addRow.apply($this, [i, config.rows[i]]);
        }
      });
    }
  };

  /**
   *
   * @param {Object|string} method
   * @returns {jQuery|methods|*}
   */
  // eslint-disable-next-line no-param-reassign

  $.fn.timeSchedule = function (method) {
    // Method calling logic
    if (methods[method]) {
      return methods[method].apply(this, Array.prototype.slice.call(arguments, 1)); // eslint-disable-next-line no-else-return
    } else if (_typeof(method) === 'object' || !method) {
      return methods.init.apply(this, arguments);
    }

    $.error('Method ' + method + ' does not exist on jQuery.timeSchedule');
    return this;
  };

})(jQuery);
