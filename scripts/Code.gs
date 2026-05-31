/**
 * Kesha Finance Tracker — Google Sheets Apps Script
 *
 * Скопируй в Расширения → Apps Script в таблице и запусти setupSheets() один раз.
 */

// ============================================================
// КОНФИГУРАЦИЯ
// ============================================================

// Цвета категорий — соответствуют боту Kesha
var CATEGORY_COLORS = {
  // Расходы
  'Кофе':          '#5C4033',  // коричневый (кофейный)
  'Еда':           '#E65100',  // оранжевый
  'Такси':         '#FFD600',  // жёлтый
  'Одежда':        '#E91E63',  // розовый
  'Красота':       '#F48FB1',  // светло-розовый
  'Подписки':      '#7C4DFF',  // фиолетовый
  'Дом':           '#795548',  // коричневый
  'Подарки':       '#FF4081',  // ярко-розовый
  'Маркетплейсы':  '#00BCD4',  // cyan
  'Здоровье':      '#4CAF50',  // зелёный
  'Развлечения':   '#FF9800',  // оранжевый
  'Другое':        '#9E9E9E',  // серый

  // Доходы
  'Зарплата':      '#2E7D32',  // тёмно-зелёный
  'Фриланс':       '#1B5E20',  // зелёный
  'Подарок':       '#FF4081',  // розовый (как подарки)
  'Инвестиции':    '#0D47A1',  // синий
  'Возврат долга': '#4CAF50',  // зелёный
};

var DEFAULT_COLOR = '#F5F5F5';

// ============================================================
// НАСТРОЙКА ТАБЛИЦЫ — запустить один раз
// ============================================================

function setupSheets() {
  createTransactionsSheet();
  createBudgetsSheet();
  createCategoriesSheet();
  createSettingsSheet();

  SpreadsheetApp.getUi().alert(
    '✅ Kesha готов!\n\n' +
    'Созданы листы: Transactions, Budgets, Categories, Settings\n\n' +
    'Осталось скопировать .env в бота и запустить.'
  );
}

// --- Transactions ---

function createTransactionsSheet() {
  var sheet = getOrCreateSheet('Transactions');
  sheet.clear();

  var headers = [
    'Month', 'Date', 'Type', 'Amount UAH', 'Amount USD', 'Amount EUR',
    'Category', 'AI Comment', 'Source'
  ];

  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  sheet.getRange(1, 1, 1, headers.length)
    .setFontWeight('bold')
    .setBackground('#1e293b')
    .setFontColor('#fbbf24');

  sheet.setFrozenRows(1);

  // Валидация для Type (колонка C)
  var typeRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['income', 'expense'], true)
    .build();
  sheet.getRange('C2:C').setDataValidation(typeRule);

  formatTransactionsSheet(sheet);
}

function formatTransactionsSheet(sheet) {
  // Формат даты
  sheet.getRange('B2:B').setNumberFormat('dd.mm.yyyy');
  // Формат сумм
  sheet.getRange('D2:F').setNumberFormat('#,##0.00');

  // Ширина колонок
  sheet.setColumnWidth(1, 100);   // Month
  sheet.setColumnWidth(2, 90);    // Date
  sheet.setColumnWidth(3, 80);    // Type
  sheet.setColumnWidth(4, 100);   // Amount UAH
  sheet.setColumnWidth(5, 100);   // Amount USD
  sheet.setColumnWidth(6, 100);   // Amount EUR
  sheet.setColumnWidth(7, 150);   // Category
  sheet.setColumnWidth(8, 250);   // Comment
  sheet.setColumnWidth(9, 200);   // Source
}

// --- Budgets ---

function createBudgetsSheet() {
  var sheet = getOrCreateSheet('Budgets');
  sheet.clear();

  var headers = ['Month', 'Category', 'Limit', 'Type'];
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  sheet.getRange(1, 1, 1, headers.length)
    .setFontWeight('bold')
    .setBackground('#1e293b')
    .setFontColor('#fbbf24');
  sheet.setFrozenRows(1);

  // Валидация
  var typeRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['budget', 'limit'], true)
    .build();
  sheet.getRange('D2:D').setDataValidation(typeRule);

  sheet.setColumnWidth(1, 100);
  sheet.setColumnWidth(2, 150);
  sheet.setColumnWidth(3, 100);
  sheet.setColumnWidth(4, 80);
}

// --- Categories ---

function createCategoriesSheet() {
  var sheet = getOrCreateSheet('Categories');
  sheet.clear();

  var headers = ['Type', 'Category'];
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  sheet.getRange(1, 1, 1, headers.length)
    .setFontWeight('bold')
    .setBackground('#1e293b')
    .setFontColor('#fbbf24');
  sheet.setFrozenRows(1);

  var typeRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['expense', 'income'], true)
    .build();
  sheet.getRange('A2:A').setDataValidation(typeRule);

  sheet.setColumnWidth(1, 100);
  sheet.setColumnWidth(2, 250);
}

// --- Settings ---

function createSettingsSheet() {
  var sheet = getOrCreateSheet('Settings');
  sheet.clear();

  var headers = ['Key', 'Value'];
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  sheet.getRange(1, 1, 1, headers.length)
    .setFontWeight('bold')
    .setBackground('#1e293b')
    .setFontColor('#fbbf24');
  sheet.setFrozenRows(1);

  sheet.setColumnWidth(1, 200);
  sheet.setColumnWidth(2, 200);
}

// ============================================================
// АВТОМАТИЧЕСКОЕ ФОРМАТИРОВАНИЕ (onEdit)
// ============================================================

function onEdit(e) {
  if (!e) return;

  var sheet = e.source.getActiveSheet();
  if (sheet.getName() !== 'Transactions') return;

  var range = e.range;
  var row = range.getRow();
  var col = range.getColumn();

  // Раскрашиваем строку по категории (колонка G)
  if (col === 7) {  // Category column
    var category = range.getValue();
    var color = CATEGORY_COLORS[category] || DEFAULT_COLOR;
    sheet.getRange(row, 1, 1, 9).setBackground(color);
  }

  // Авто-заполнение месяца из даты
  if (col === 2) {  // Date column
    var dateValue = range.getValue();
    if (dateValue instanceof Date) {
      sheet.getRange(row, 1).setValue(
        Utilities.formatDate(dateValue, Session.getScriptTimeZone(), 'MMMM')
      );
    }
  }
}

// ============================================================
// МЕНЮ (доступно в таблице)
// ============================================================

function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('🧮 Kesha')
    .addItem('⚙️ Настроить таблицу', 'setupSheets')
    .addSeparator()
    .addItem('📊 Отчёт за месяц', 'generateMonthlyReport')
    .addItem('🎨 Применить цвета', 'applyColorsToAll')
    .addToUi();
}

function applyColorsToAll() {
  var sheet = SpreadsheetApp.getActive().getSheetByName('Transactions');
  if (!sheet) return;

  var data = sheet.getDataRange().getValues();
  for (var i = 1; i < data.length; i++) {
    var category = data[i][6];  // колонка G
    var color = CATEGORY_COLORS[category] || DEFAULT_COLOR;
    if (category) {
      sheet.getRange(i + 1, 1, 1, 9).setBackground(color);
    }
  }
  SpreadsheetApp.getUi().alert('🎨 Цвета применены к ' + (data.length - 1) + ' строкам');
}

// ============================================================
// ОТЧЁТЫ
// ============================================================

function generateMonthlyReport() {
  var ss = SpreadsheetApp.getActive();
  var transactions = ss.getSheetByName('Transactions');
  if (!transactions) return;

  var data = transactions.getDataRange().getValues();
  var now = new Date();
  var currentMonth = Utilities.formatDate(now, Session.getScriptTimeZone(), 'MMMM');

  // Группируем по категориям
  var expensesByCategory = {};
  var incomeByCategory = {};
  var totalExpense = 0, totalIncome = 0;

  for (var i = 1; i < data.length; i++) {
    var row = data[i];
    var month = row[0];
    var type = String(row[2]).toLowerCase();
    var amount = Number(row[3]) || 0;
    var category = row[6] || 'Другое';

    if (month !== currentMonth) continue;

    if (type === 'expense') {
      expensesByCategory[category] = (expensesByCategory[category] || 0) + Math.abs(amount);
      totalExpense += Math.abs(amount);
    } else if (type === 'income') {
      incomeByCategory[category] = (incomeByCategory[category] || 0) + amount;
      totalIncome += amount;
    }
  }

  // Создаём лист отчёта
  var reportName = 'Report_' + currentMonth;
  var reportSheet = getOrCreateSheet(reportName);
  reportSheet.clear();

  reportSheet.getRange('A1').setValue('📊 Финансовый отчёт — ' + currentMonth + ' ' + now.getFullYear());
  reportSheet.getRange('A1:B1').merge();
  reportSheet.getRange('A1').setFontWeight('bold').setFontSize(14);

  // Доходы
  var row = 3;
  reportSheet.getRange('A' + row).setValue('💰 Доходы').setFontWeight('bold');
  reportSheet.getRange('B' + row).setValue(Number(totalIncome).toFixed(2) + ' UAH');
  row = 4;
  for (var cat in incomeByCategory) {
    reportSheet.getRange('A' + row).setValue('   ' + cat);
    reportSheet.getRange('B' + row).setValue(Number(incomeByCategory[cat]).toFixed(2));
    row++;
  }

  // Расходы
  row++;
  reportSheet.getRange('A' + row).setValue('💸 Расходы').setFontWeight('bold');
  reportSheet.getRange('B' + row).setValue(Number(totalExpense).toFixed(2) + ' UAH');
  row++;
  for (var cat in expensesByCategory) {
    reportSheet.getRange('A' + row).setValue('   ' + cat);
    reportSheet.getRange('B' + row).setValue(Number(expensesByCategory[cat]).toFixed(2));
    row++;
  }

  // Итог
  row++;
  var balance = totalIncome - totalExpense;
  reportSheet.getRange('A' + row).setValue('📈 Итого').setFontWeight('bold');
  reportSheet.getRange('B' + row).setValue(Number(balance).toFixed(2) + ' UAH');
  reportSheet.getRange('A' + row + ':B' + row)
    .setFontWeight('bold')
    .setBackground(balance >= 0 ? '#E8F5E9' : '#FFEBEE');

  reportSheet.setColumnWidth(1, 250);
  reportSheet.setColumnWidth(2, 150);

  SpreadsheetApp.getUi().alert(
    '✅ Отчёт создан!\n\n' +
    'Лист: ' + reportName + '\n' +
    'Доход: +' + totalIncome.toFixed(0) + ' UAH\n' +
    'Расход: -' + totalExpense.toFixed(0) + ' UAH\n' +
    'Баланс: ' + (balance >= 0 ? '+' : '') + balance.toFixed(0) + ' UAH'
  );
}

// ============================================================
// УТИЛИТЫ
// ============================================================

function getOrCreateSheet(name) {
  var ss = SpreadsheetApp.getActive();
  var sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
  }
  return sheet;
}
